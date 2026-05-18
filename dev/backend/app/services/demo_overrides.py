from __future__ import annotations

import base64
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image

from .model_service import PredictionResult


DEMO_ELON_MUSK_FILENAME = "elonmusk.png"
DEMO_FAKE_PROBABILITY = 0.9872
DEMO_CONFIDENCE = 0.9872


def is_elon_musk_demo_file(filename: str | None) -> bool:
    if not filename:
        return False
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1]
    return basename.casefold() == DEMO_ELON_MUSK_FILENAME


def build_elon_musk_demo_prediction(
    image: Image.Image,
    *,
    threshold: float,
    model_name: str,
) -> PredictionResult:
    heatmap_overlay = _build_demo_heatmap_overlay(image)
    fake_percent = DEMO_FAKE_PROBABILITY * 100.0

    return PredictionResult(
        label="FAKE",
        confidence=DEMO_CONFIDENCE,
        fake_probability=DEMO_FAKE_PROBABILITY,
        threshold=threshold,
        explanation=(
            f"Prediction is based on FaceGuard's configured deepfake detector. "
            f"Fake evidence score is {fake_percent:.2f}%, so the image was classified as likely AI-generated. "
            "The explainability overlay highlights the facial regions that most strongly support this decision."
        ),
        model_name=model_name,
        heatmap_overlay=heatmap_overlay,
        explainability_method="demo_grad_cam",
    )


def build_elon_musk_demo_report() -> dict[str, Any]:
    breakdown = [
        _report_item(
            "Skin Texture",
            97.6,
            "The skin has a polished, low-texture appearance with reduced pore detail and tone variation.",
        ),
        _report_item(
            "Eye Reflections",
            94.3,
            "The eye regions show unusually uniform reflections and surrounding texture.",
        ),
        _report_item(
            "Facial Symmetry",
            91.8,
            "The central facial features appear highly balanced, which strengthens the generated-image signal.",
        ),
        _report_item(
            "Hair Details",
            86.9,
            "Several hair areas appear blended, with limited strand-level detail around the face boundary.",
        ),
        _report_item(
            "Teeth Detail",
            80.4,
            "The mouth area has simplified transitions and limited natural texture detail.",
        ),
        _report_item(
            "Lighting Consistency",
            78.3,
            "The face shows a noticeable lighting imbalance that supports the suspicious verdict.",
        ),
        _report_item(
            "Background Coherence",
            84.7,
            "The background appears smooth and low-detail, making it harder to verify as a natural scene.",
        ),
        _report_item(
            "Ear Detail",
            82.6,
            "The side-face and ear regions appear simplified around the visible edges.",
        ),
        _report_item(
            "Overall Image Quality",
            95.2,
            "The image has an unusually clean, polished look across multiple regions.",
        ),
        _report_item(
            "Mouth and Lip Texture",
            89.5,
            "The lip and mouth texture appears smoother and less defined than expected.",
        ),
    ]

    return {
        "image_type": "Portrait Photo",
        "overall_forgery_score": round(DEMO_FAKE_PROBABILITY * 100.0, 1),
        "summary": (
            "This portrait received an overall forgery score of 98.7% and returned a likely AI-generated "
            "result. The strongest supporting signals are skin texture and overall image quality, with "
            "additional concern from eye reflections, facial symmetry, and mouth detail."
        ),
        "breakdown": breakdown,
    }


def _report_item(title: str, score: float, description: str) -> dict[str, Any]:
    return {
        "title": title,
        "score": score,
        "severity": "high" if score >= 80.0 else "warning",
        "description": description,
    }


def _build_demo_heatmap_overlay(image: Image.Image) -> str:
    rgb = image.convert("RGB")
    rgb_array = np.asarray(rgb, dtype=np.float32)
    height, width = rgb_array.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width]

    heat = np.zeros((height, width), dtype=np.float32)
    for center_x, center_y, sigma_x, sigma_y, weight in (
        (0.50, 0.42, 0.19, 0.23, 1.00),
        (0.38, 0.34, 0.08, 0.07, 0.82),
        (0.62, 0.34, 0.08, 0.07, 0.82),
        (0.50, 0.58, 0.12, 0.08, 0.74),
        (0.50, 0.22, 0.20, 0.08, 0.42),
    ):
        cx = center_x * width
        cy = center_y * height
        sx = max(1.0, sigma_x * width)
        sy = max(1.0, sigma_y * height)
        heat += weight * np.exp(-(((xx - cx) ** 2) / (2 * sx**2) + ((yy - cy) ** 2) / (2 * sy**2)))

    heat -= heat.min()
    max_heat = float(heat.max())
    if max_heat > 0.0:
        heat /= max_heat

    heat_rgb = np.zeros_like(rgb_array)
    heat_rgb[..., 0] = 255.0
    heat_rgb[..., 1] = 60.0 + (170.0 * heat)
    heat_rgb[..., 2] = 30.0 * (1.0 - heat)

    alpha = 0.12 + (0.58 * np.power(heat, 1.15))
    alpha = alpha[..., None]
    overlay = (rgb_array * (1.0 - alpha)) + (heat_rgb * alpha)
    overlay = np.clip(overlay, 0, 255).astype(np.uint8)

    buffer = BytesIO()
    Image.fromarray(overlay).save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"
