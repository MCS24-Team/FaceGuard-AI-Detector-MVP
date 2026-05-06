"""
Model inference and Grad-CAM explainability service with a pluggable registry.

To add a new model:
  1. Define its nn.Module class in architectures.py.
  2. Write a build function and an output-extractor function here.
  3. Add one entry to MODEL_REGISTRY.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Any, Callable

import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F

from .architectures import FairDetector, Xception
from .clip_vit_detector import ClipVitLargeDeepfakeDetector

try:
    from pytorch_grad_cam import GradCAM
    from pytorch_grad_cam.utils.image import show_cam_on_image
except ImportError:  # pragma: no cover
    GradCAM = None  # type: ignore[assignment]
    show_cam_on_image = None  # type: ignore[assignment]


@dataclass
class PredictionResult:
    label: str
    confidence: float
    fake_probability: float
    threshold: float
    explanation: str
    model_name: str
    heatmap_overlay: str | None
    explainability_method: str


@dataclass(frozen=True)
class ModelSpec:
    """Everything the InferenceService needs to build and run a model."""

    build_fn: Callable[[], nn.Module]
    image_size: int
    mean: tuple[float, ...]
    std: tuple[float, ...]
    description: str
    extract_prob: Callable[[Any], float]


class _BinaryLogitTarget:
    """
    Target fake evidence when predicted FAKE, otherwise target real evidence.
    """

    def __init__(self, label: str) -> None:
        self._sign = 1.0 if label == "FAKE" else -1.0

    def __call__(self, model_output: torch.Tensor) -> torch.Tensor:
        logits = model_output
        if logits.ndim > 1:
            logits = logits[:, 0]
        return logits * self._sign


class _CamModelAdapter(nn.Module):
    """
    Adapts model outputs into a simple logits tensor expected by Grad-CAM.
    """

    def __init__(self, model: nn.Module, model_name: str) -> None:
        super().__init__()
        self.model = model
        self.model_name = model_name.lower()

    def forward(self, image_tensor: torch.Tensor) -> torch.Tensor:
        if "pg_fdd" in self.model_name and isinstance(self.model, FairDetector):
            output = self.model({"image": image_tensor}, inference=True)["cls"]
            return output

        output = self.model(image_tensor)
        if isinstance(output, tuple):
            output = output[0]
        elif isinstance(output, dict):
            if "cls" in output:
                output = output["cls"]
            elif "logits" in output:
                output = output["logits"]
            elif "logits_labels" in output:
                output = output["logits_labels"]

        if not isinstance(output, torch.Tensor):
            raise TypeError("Grad-CAM adapter expected tensor logits output.")
        return output


def _build_vit() -> nn.Module:
    from torchvision import models

    model = models.vit_b_16(weights=None)
    model.heads[0] = nn.Linear(768, 1)
    return model


def _build_xception() -> nn.Module:
    return Xception({"mode": "original", "num_classes": 1, "inc": 3, "dropout": False})


def _build_pg_fdd() -> nn.Module:
    return FairDetector()


def _build_clip_vit() -> nn.Module:
    return ClipVitLargeDeepfakeDetector()


def _extract_sigmoid_scalar(output: Any) -> float:
    logits = output
    if logits.ndim > 1:
        logits = logits.squeeze(1)
    return torch.sigmoid(logits)[0].item()


def _extract_xception(output: Any) -> float:
    logits, _ = output
    if logits.ndim > 1:
        logits = logits.squeeze(1)
    return torch.sigmoid(logits)[0].item()


def _extract_pg_fdd(output: Any) -> float:
    logits = output["cls"]
    if logits.ndim > 1:
        logits = logits.squeeze(1)
    return torch.sigmoid(logits)[0].item()


def _extract_clip_vit(output: Any) -> float:
    logits = output["logits_labels"] if isinstance(output, dict) else output.logits_labels
    probabilities = torch.softmax(logits, dim=-1)
    return probabilities[0, 1].item()


MODEL_REGISTRY: dict[str, ModelSpec] = {
    "clip_vit": ModelSpec(
        build_fn=_build_clip_vit,
        image_size=224,
        mean=(0.48145466, 0.4578275, 0.40821073),
        std=(0.26862954, 0.26130258, 0.27577711),
        description="CLIP ViT-L/14 deepfake classifier",
        extract_prob=_extract_clip_vit,
    ),
    "vit": ModelSpec(
        build_fn=_build_vit,
        image_size=224,
        mean=(0.485, 0.456, 0.406),
        std=(0.229, 0.224, 0.225),
        description="ViT-B/16 deepfake classifier",
        extract_prob=_extract_sigmoid_scalar,
    ),
    "xception": ModelSpec(
        build_fn=_build_xception,
        image_size=256,
        mean=(0.5, 0.5, 0.5),
        std=(0.5, 0.5, 0.5),
        description="Xception deepfake classifier",
        extract_prob=_extract_xception,
    ),
    "pg_fdd": ModelSpec(
        build_fn=_build_pg_fdd,
        image_size=256,
        mean=(0.5, 0.5, 0.5),
        std=(0.5, 0.5, 0.5),
        description="PG-FDD (Fair Deepfake Detector)",
        extract_prob=_extract_pg_fdd,
    ),
}


def _resolve_spec(model_name: str) -> ModelSpec:
    name_lower = model_name.lower()
    if name_lower in MODEL_REGISTRY:
        return MODEL_REGISTRY[name_lower]

    for key, spec in MODEL_REGISTRY.items():
        if key in name_lower:
            return spec
    supported = ", ".join(MODEL_REGISTRY.keys())
    raise ValueError(f"Unknown model '{model_name}'. Supported: {supported}")


class InferenceService:
    """Generic inference service with optional Grad-CAM overlay generation."""

    def __init__(self, model_name: str, model_path: Path, threshold: float) -> None:
        self.model_name = model_name
        self.model_path = Path(model_path)
        self.threshold = threshold

        self._spec = _resolve_spec(model_name)
        self.image_size = self._spec.image_size
        self.mean = self._spec.mean
        self.std = self._spec.std

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model: nn.Module | None = None
        self._ready = False
        self._lock = Lock()

    @property
    def model_ready(self) -> bool:
        return self._ready

    def ensure_loaded(self) -> None:
        if self._ready and self._model is not None:
            return
        with self._lock:
            if self._ready and self._model is not None:
                return
            self._model = self._load_model()
            self._ready = True

    def _load_model(self) -> nn.Module:
        checkpoint_path = self._resolve_checkpoint_path()
        if not checkpoint_path.exists():
            raise FileNotFoundError(
                f"Checkpoint not found at '{checkpoint_path}'. Place the .pth file locally or configure HF_MODEL_REPO."
            )

        model = self._spec.build_fn()
        checkpoint = torch.load(checkpoint_path, map_location=self.device)

        if isinstance(checkpoint, dict):
            for wrapper_key in ("state_dict", "model_state_dict"):
                if wrapper_key in checkpoint and isinstance(checkpoint[wrapper_key], dict):
                    checkpoint = checkpoint[wrapper_key]
                    break

        model_keys = set(model.state_dict().keys())
        ckpt_keys = set(checkpoint.keys())
        if not model_keys & ckpt_keys:
            prefix = next(iter(ckpt_keys)).split(".")[0] + "."
            stripped = {k[len(prefix):]: v for k, v in checkpoint.items() if k.startswith(prefix)}
            if set(stripped.keys()) & model_keys:
                checkpoint = stripped

        model.load_state_dict(checkpoint, strict=False)
        model.to(self.device)
        model.eval()
        return model

    def _resolve_checkpoint_path(self) -> Path:
        repo_id = os.getenv("HF_MODEL_REPO")
        if not repo_id:
            return self.model_path

        try:
            from huggingface_hub import hf_hub_download
        except ImportError as exc:
            raise RuntimeError(
                "HF_MODEL_REPO is configured, but huggingface_hub is not installed."
            ) from exc

        checkpoint_file = os.getenv("HF_MODEL_FILE", self.model_path.name)
        cache_dir = os.getenv("MODEL_CACHE_DIR", "/tmp/faceguard_models")
        token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")

        return Path(
            hf_hub_download(
                repo_id=repo_id,
                filename=checkpoint_file,
                token=token,
                cache_dir=cache_dir,
            )
        )

    def _forward_model(self, image_tensor: torch.Tensor) -> Any:
        if self._model is None:
            raise RuntimeError("Model is not loaded.")

        if isinstance(self._model, FairDetector):
            return self._model({"image": image_tensor}, inference=True)
        return self._model(image_tensor)

    def _resolve_cam_targets(self) -> tuple[list[nn.Module], Callable[[torch.Tensor], torch.Tensor] | None]:
        if self._model is None:
            raise RuntimeError("Model is not loaded.")

        model_name = self.model_name.lower()
        if "vit" in model_name:
            grid_size = self.image_size // 16
            target_layers = [self._model.encoder.layers[-1].ln_1]  # type: ignore[attr-defined]

            def reshape_transform(tensor: torch.Tensor) -> torch.Tensor:
                result = tensor[:, 1:, :].reshape(tensor.size(0), grid_size, grid_size, tensor.size(2))
                return result.transpose(2, 3).transpose(1, 2)

            return target_layers, reshape_transform

        if "xception" in model_name and isinstance(self._model, Xception):
            return [self._model.bn4], None

        if "pg_fdd" in model_name and isinstance(self._model, FairDetector):
            return [self._model.block_fair.conv2d[-1]], None

        raise ValueError(f"No Grad-CAM target layer mapping for model '{self.model_name}'.")

    def _denormalize_to_rgb(self, image_tensor: torch.Tensor) -> np.ndarray:
        image = image_tensor.detach().cpu()[0].clone()
        for channel_index, (mean, std) in enumerate(zip(self.mean, self.std)):
            image[channel_index] = (image[channel_index] * std) + mean
        rgb = image.permute(1, 2, 0).numpy()
        return np.clip(rgb, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def _image_to_rgb_float(image: Image.Image) -> np.ndarray:
        rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
        return np.clip(rgb, 0.0, 1.0)

    @staticmethod
    def _resize_cam_mask(mask: np.ndarray, target_height: int, target_width: int) -> np.ndarray:
        cam_tensor = torch.from_numpy(mask).unsqueeze(0).unsqueeze(0)
        resized = F.interpolate(
            cam_tensor,
            size=(target_height, target_width),
            mode="bilinear",
            align_corners=False,
        )
        return resized[0, 0].numpy()

    @staticmethod
    def _encode_png_data_url(rgb_uint8_image: np.ndarray) -> str:
        pil_image = Image.fromarray(rgb_uint8_image)
        buffer = BytesIO()
        pil_image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    def _generate_grad_cam_overlay(
        self,
        image_tensor: torch.Tensor,
        label: str,
        source_image: Image.Image | None = None,
    ) -> str | None:
        if "clip_vit" in self.model_name.lower():
            return None

        if self._model is None or GradCAM is None or show_cam_on_image is None:
            return None

        try:
            target_layers, reshape_transform = self._resolve_cam_targets()
            cam_model = _CamModelAdapter(self._model, self.model_name).to(self.device)
            cam_model.eval()
            targets = [_BinaryLogitTarget(label)]

            with GradCAM(model=cam_model, target_layers=target_layers, reshape_transform=reshape_transform) as cam:
                grayscale_cam = cam(
                    input_tensor=image_tensor,
                    targets=targets,
                    aug_smooth=False,
                    eigen_smooth=False,
                )
                grayscale_cam = grayscale_cam[0, :]

            if source_image is not None:
                rgb_image = self._image_to_rgb_float(source_image)
            else:
                rgb_image = self._denormalize_to_rgb(image_tensor)

            target_height, target_width = rgb_image.shape[0], rgb_image.shape[1]
            if grayscale_cam.shape != (target_height, target_width):
                grayscale_cam = self._resize_cam_mask(
                    mask=grayscale_cam,
                    target_height=target_height,
                    target_width=target_width,
                )

            overlay = show_cam_on_image(rgb_image, grayscale_cam, use_rgb=True)
            return self._encode_png_data_url(overlay)
        except Exception:
            return None

    def _build_explanation(self, fake_probability: float, label: str, has_heatmap: bool) -> str:
        threshold_percent = round(self.threshold * 100, 1)
        fake_percent = round(fake_probability * 100, 2)
        if label == "FAKE":
            outcome_text = (
                f"Fake evidence score is {fake_percent}%, above the decision threshold ({threshold_percent}%)."
            )
        else:
            outcome_text = (
                f"Fake evidence score is {fake_percent}%, below the decision threshold ({threshold_percent}%)."
            )

        if has_heatmap:
            return (
                f"Prediction is based on {self._spec.description}. {outcome_text} "
                "The Grad-CAM overlay highlights image regions that most influenced this decision."
            )
        return (
            f"Prediction is based on {self._spec.description}. {outcome_text} "
            "Grad-CAM overlay was unavailable for this request."
        )

    def predict(self, image_tensor: torch.Tensor, source_image: Image.Image | None = None) -> PredictionResult:
        with torch.no_grad():
            output = self._forward_model(image_tensor)
            fake_probability = self._spec.extract_prob(output)

        is_fake = fake_probability >= self.threshold
        label = "FAKE" if is_fake else "REAL"
        confidence = fake_probability if is_fake else 1.0 - fake_probability

        heatmap_overlay = self._generate_grad_cam_overlay(
            image_tensor=image_tensor,
            label=label,
            source_image=source_image,
        )
        explanation = self._build_explanation(
            fake_probability=fake_probability,
            label=label,
            has_heatmap=heatmap_overlay is not None,
        )

        return PredictionResult(
            label=label,
            confidence=round(confidence, 4),
            fake_probability=round(fake_probability, 4),
            threshold=self.threshold,
            explanation=explanation,
            model_name=self.model_name,
            heatmap_overlay=heatmap_overlay,
            explainability_method="grad_cam" if heatmap_overlay is not None else "none",
        )


def model_service_from_settings(settings: Any) -> InferenceService:
    return InferenceService(
        model_name=settings.model_name,
        model_path=settings.model_path,
        threshold=settings.fake_threshold,
    )
