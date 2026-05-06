from __future__ import annotations

from collections import OrderedDict
from typing import Any

import torch
import torch.nn as nn


class ClipVitLargeDeepfakeDetector(nn.Module):
    """Inference-only loader for the CLIP ViT-L/14 Lightning checkpoint."""

    def __init__(self) -> None:
        super().__init__()

        try:
            from transformers import CLIPVisionConfig, CLIPVisionModel
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "The clip_vit model requires transformers. Install it with `pip install transformers`."
            ) from exc

        config = CLIPVisionConfig(
            hidden_size=1024,
            intermediate_size=4096,
            num_hidden_layers=24,
            num_attention_heads=16,
            image_size=224,
            patch_size=14,
            hidden_act="quick_gelu",
            layer_norm_eps=1e-5,
        )
        self.feature_extractor = CLIPVisionModel(config)
        self.linear = nn.Linear(config.hidden_size, 2)

    def forward(self, pixel_values: torch.Tensor) -> dict[str, torch.Tensor]:
        outputs = self.feature_extractor(pixel_values=pixel_values)
        logits = self.linear(outputs.pooler_output)
        return {"logits_labels": logits}

    def load_state_dict(
        self,
        state_dict: dict[str, Any],
        strict: bool = True,
        assign: bool = False,
    ) -> Any:
        converted = self._convert_checkpoint_state_dict(state_dict)
        return super().load_state_dict(converted, strict=False, assign=assign)

    @staticmethod
    def _convert_checkpoint_state_dict(state_dict: dict[str, Any]) -> OrderedDict[str, Any]:
        converted: OrderedDict[str, Any] = OrderedDict()
        feature_prefix = "feature_extractor.base_model.model."
        classifier_prefix = "model.linear."

        for key, value in state_dict.items():
            if key.startswith(feature_prefix):
                suffix = key[len(feature_prefix):]

                if ".ln_tuning_layers.default." in suffix:
                    suffix = suffix.replace(".ln_tuning_layers.default.", ".")
                elif ".base_layer." in suffix:
                    continue

                converted[f"feature_extractor.{suffix}"] = value
                if suffix.startswith("vision_model."):
                    converted[f"feature_extractor.{suffix[len('vision_model.'):]}"] = value
                continue

            if key.startswith(classifier_prefix):
                converted[f"linear.{key[len(classifier_prefix):]}"] = value
                continue

            if key.startswith("feature_extractor.") or key.startswith("linear."):
                converted[key] = value

        return converted
