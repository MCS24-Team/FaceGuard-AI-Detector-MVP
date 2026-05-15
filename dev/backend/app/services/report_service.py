from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from PIL import Image


@dataclass
class FaceSignal:
    bbox: tuple[int, int, int, int] | None
    landmarks: np.ndarray | None
    available: bool


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _round_score(value: float) -> float:
    return round(_clamp(value), 1)


def _severity(score: float) -> str:
    if score >= 80:
        return "high"
    if score >= 60:
        return "warning"
    if score >= 40:
        return "mild"
    return "normal"


def _to_rgb_array(image: Image.Image) -> np.ndarray:
    return np.array(image.convert("RGB"))


def _gray(region: np.ndarray) -> np.ndarray:
    if region.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)
    return cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)


def _texture_gray(region: np.ndarray) -> np.ndarray:
    gray = _gray(region)
    if gray.size <= 1:
        return gray
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _sharpness(region: np.ndarray) -> float:
    return float(cv2.Laplacian(_texture_gray(region), cv2.CV_64F).var())


def _edge_density(region: np.ndarray) -> float:
    edges = cv2.Canny(_texture_gray(region), 80, 160)
    return float(edges.mean() / 255.0)


def _brightness(region: np.ndarray) -> float:
    return float(_gray(region).mean())


def _detail_anomaly(region: np.ndarray) -> float:
    sharp = _sharpness(region)
    edges = _edge_density(region)
    blur_signal = 100.0 - _clamp((sharp / 220.0) * 100.0)
    sparse_edges = 100.0 - _clamp((edges / 0.12) * 100.0)
    return _clamp((blur_signal * 0.65) + (sparse_edges * 0.35))


def _clip_bbox(
    bbox: tuple[int, int, int, int],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    return (
        max(0, min(width - 1, x1)),
        max(0, min(height - 1, y1)),
        max(1, min(width, x2)),
        max(1, min(height, y2)),
    )


def _crop(region_source: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    height, width = region_source.shape[:2]
    x1, y1, x2, y2 = _clip_bbox(bbox, width, height)
    if x2 <= x1 or y2 <= y1:
        return region_source
    return region_source[y1:y2, x1:x2]


def _point_region(
    point: np.ndarray,
    image_shape: tuple[int, int, int],
    radius: int,
) -> tuple[int, int, int, int]:
    height, width = image_shape[:2]
    x, y = int(point[0]), int(point[1])
    return _clip_bbox((x - radius, y - radius, x + radius, y + radius), width, height)


def _mouth_region(
    landmarks: np.ndarray,
    image_shape: tuple[int, int, int],
    radius: int,
) -> tuple[int, int, int, int]:
    height, width = image_shape[:2]
    mouth_points = landmarks[3:5]
    x1 = int(np.min(mouth_points[:, 0])) - radius
    x2 = int(np.max(mouth_points[:, 0])) + radius
    y1 = int(np.min(mouth_points[:, 1])) - radius
    y2 = int(np.max(mouth_points[:, 1])) + radius
    return _clip_bbox((x1, y1, x2, y2), width, height)


class ReportService:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._face_app: Any | None = None
        self._face_app_attempted = False
        self._face_app_error: str | None = None

    def build_report(
        self,
        image: Image.Image,
        fake_probability: float,
        label: str,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        rgb = _to_rgb_array(image)
        overall_score = _round_score(fake_probability * 100.0)
        face_signal = self._detect_primary_face(rgb)

        breakdown = [
            self._skin_texture(rgb, face_signal, overall_score),
            self._eye_consistency(rgb, face_signal, overall_score),
            self._facial_symmetry(rgb, face_signal, overall_score),
            self._hair_detail(rgb, face_signal, overall_score),
            self._teeth_detail(rgb, face_signal, overall_score),
            self._lighting_consistency(rgb, face_signal, overall_score),
            self._background_complexity(rgb, face_signal, overall_score),
            self._ear_detail(rgb, face_signal, overall_score),
            self._overall_image_quality(rgb, overall_score),
            self._mouth_detail(rgb, face_signal, overall_score),
        ]

        return {
            "image_type": "Portrait Photo" if face_signal.available else "Uploaded Image",
            "overall_forgery_score": overall_score,
            "summary": self._summary(overall_score, label, breakdown, face_signal.available),
            "breakdown": breakdown,
        }

    def _get_face_app(self) -> Any | None:
        if self._face_app_attempted:
            return self._face_app

        self._face_app_attempted = True
        try:
            from insightface.app import FaceAnalysis

            face_app = FaceAnalysis(name="buffalo_s", providers=["CPUExecutionProvider"])
            face_app.prepare(ctx_id=-1, det_size=(640, 640))
            self._face_app = face_app
        except Exception as exc:
            self._face_app_error = str(exc)
            self._face_app = None

        return self._face_app

    def _detect_primary_face(self, rgb: np.ndarray) -> FaceSignal:
        face_app = self._get_face_app()
        if face_app is None:
            return FaceSignal(bbox=None, landmarks=None, available=False)

        try:
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            faces = face_app.get(bgr)
        except Exception as exc:
            self._face_app_error = str(exc)
            return FaceSignal(bbox=None, landmarks=None, available=False)

        if not faces:
            return FaceSignal(bbox=None, landmarks=None, available=False)

        face = max(
            faces,
            key=lambda item: float((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])),
        )
        height, width = rgb.shape[:2]
        bbox = _clip_bbox(tuple(int(v) for v in face.bbox), width, height)
        landmarks = getattr(face, "kps", None)
        if landmarks is not None:
            landmarks = np.asarray(landmarks, dtype=np.float32)
        return FaceSignal(bbox=bbox, landmarks=landmarks, available=True)

    def _facial_symmetry(
        self,
        rgb: np.ndarray,
        face_signal: FaceSignal,
        overall_score: float,
    ) -> dict[str, Any]:
        if face_signal.landmarks is None or len(face_signal.landmarks) < 5:
            score = _round_score(overall_score * 0.9)
            variants = self._description_variants(
                normal="The face shows ordinary balance, with no strong symmetry concern visible.",
                mild="The facial structure appears broadly balanced, but this is only a soft supporting signal.",
                warning="The face appears unusually even around the central features, which can sometimes appear in generated portraits.",
                high="The facial structure looks very evenly arranged, making symmetry one of the stronger suspicious signals in this image.",
            )
        else:
            left_eye, right_eye, nose, left_mouth, right_mouth = face_signal.landmarks[:5]
            eye_balance = abs(np.linalg.norm(left_eye - nose) - np.linalg.norm(right_eye - nose))
            mouth_balance = abs(np.linalg.norm(left_mouth - nose) - np.linalg.norm(right_mouth - nose))
            face_width = max(1.0, abs(right_eye[0] - left_eye[0]) * 2.2)
            asymmetry = _clamp(((eye_balance + mouth_balance) / face_width) * 220.0)
            too_symmetric = _clamp(55.0 - asymmetry)
            score = _round_score((overall_score * 0.45) + (too_symmetric * 0.35) + (asymmetry * 0.2))
            variants = self._description_variants(
                normal="The face has a natural amount of asymmetry, which lowers concern in this area.",
                mild="The main facial features appear slightly more balanced than usual, but still within a plausible natural range.",
                warning="The face appears unusually even around the eyes, nose, and mouth, which can sometimes appear in generated portraits.",
                high="The face shows a very polished, near-perfect balance around central features, making symmetry a stronger warning sign.",
            )
        return self._item("Facial Symmetry", self._calibrated_score(score, overall_score), variants)

    def _eye_consistency(
        self,
        rgb: np.ndarray,
        face_signal: FaceSignal,
        overall_score: float,
    ) -> dict[str, Any]:
        if face_signal.landmarks is None or len(face_signal.landmarks) < 2:
            score = _round_score(overall_score * 0.9)
            variants = self._description_variants(
                normal="The eye area does not show strong reflection irregularities from the visible image.",
                mild="The eye area is not clear enough for a precise reflection reading, but it shows a small amount of concern.",
                warning="The visible eye region appears somewhat uniform, which can sometimes happen with generated or heavily edited portraits.",
                high="The eye region appears unusually uniform or simplified, making the reflections and eye texture a stronger warning sign.",
            )
        else:
            left_eye, right_eye = face_signal.landmarks[:2]
            eye_distance = max(12, int(abs(right_eye[0] - left_eye[0]) * 0.35))
            left_crop = _crop(rgb, _point_region(left_eye, rgb.shape, eye_distance))
            right_crop = _crop(rgb, _point_region(right_eye, rgb.shape, eye_distance))
            brightness_gap = abs(_brightness(left_crop) - _brightness(right_crop)) / 255.0
            edge_gap = abs(_edge_density(left_crop) - _edge_density(right_crop))
            similarity_signal = 100.0 - _clamp((brightness_gap * 260.0) + (edge_gap * 520.0))
            score = _round_score((overall_score * 0.5) + (similarity_signal * 0.5))
            variants = self._description_variants(
                normal="The eye reflections and surrounding texture look reasonably natural from the visible image.",
                mild="The eye regions show some similarity in brightness and detail, but not enough to be a strong warning.",
                warning="The catchlights and eye texture appear unusually even, which can be associated with generated portraits.",
                high="The eye regions show strong uniformity in reflections or texture, making this one of the more suspicious areas.",
            )
        return self._item("Eye Reflections", self._calibrated_score(score, overall_score), variants)

    def _skin_texture(
        self,
        rgb: np.ndarray,
        face_signal: FaceSignal,
        overall_score: float,
    ) -> dict[str, Any]:
        if face_signal.bbox is None:
            region = rgb
        else:
            x1, y1, x2, y2 = face_signal.bbox
            face_w = x2 - x1
            face_h = y2 - y1
            region = _crop(
                rgb,
                (
                    x1 + int(face_w * 0.2),
                    y1 + int(face_h * 0.22),
                    x2 - int(face_w * 0.2),
                    y1 + int(face_h * 0.72),
                ),
            )

        texture_signal = _detail_anomaly(region)
        score = _round_score((overall_score * 0.45) + (texture_signal * 0.55))
        variants = self._description_variants(
            normal="The skin texture shows enough natural variation, with no strong smoothing concern.",
            mild="The skin appears slightly smooth, but the effect is mild and could come from lighting or image compression.",
            warning="The skin appears overly smooth in places, with reduced pore detail or tone variation that can suggest digital smoothing.",
            high="The skin has a polished, low-texture appearance, making smoothness one of the stronger AI-generation signals.",
        )
        return self._item("Skin Texture", self._calibrated_score(score, overall_score), variants)

    def _mouth_detail(
        self,
        rgb: np.ndarray,
        face_signal: FaceSignal,
        overall_score: float,
    ) -> dict[str, Any]:
        if face_signal.landmarks is None or len(face_signal.landmarks) < 5:
            score = _round_score(overall_score * 0.85)
            variants = self._description_variants(
                normal="The mouth area does not show a strong visible artifact from this image.",
                mild="The mouth area is not fully clear, so this is only a mild supporting signal.",
                warning="The mouth area appears somewhat simplified or smooth, which can happen in generated faces.",
                high="The mouth and lip texture appears strongly simplified, making this a more suspicious region.",
            )
        else:
            left_mouth, right_mouth = face_signal.landmarks[3:5]
            radius = max(12, int(abs(right_mouth[0] - left_mouth[0]) * 0.55))
            region = _crop(rgb, _mouth_region(face_signal.landmarks, rgb.shape, radius))
            mouth_signal = _detail_anomaly(region)
            score = _round_score((overall_score * 0.45) + (mouth_signal * 0.55))
            variants = self._description_variants(
                normal="The lips and mouth edges show enough natural texture and transition detail.",
                mild="The mouth region is slightly soft, but the visible detail is still fairly plausible.",
                warning="The lips and mouth texture appear smoother or less defined than expected, which can appear in generated faces.",
                high="The mouth area has noticeably soft edges or simplified texture, making it a stronger suspicious signal.",
            )
        return self._item("Mouth and Lip Texture", self._calibrated_score(score, overall_score), variants)

    def _hair_detail(
        self,
        rgb: np.ndarray,
        face_signal: FaceSignal,
        overall_score: float,
    ) -> dict[str, Any]:
        height, width = rgb.shape[:2]
        if face_signal.bbox is None:
            region = rgb[: max(1, height // 3), :]
        else:
            x1, y1, x2, _ = face_signal.bbox
            face_width = x2 - x1
            region = _crop(
                rgb,
                (
                    x1 - int(face_width * 0.15),
                    max(0, y1 - int(face_width * 0.55)),
                    x2 + int(face_width * 0.15),
                    y1 + int(face_width * 0.18),
                ),
            )

        hair_signal = _detail_anomaly(region)
        score = _round_score((overall_score * 0.35) + (hair_signal * 0.65))
        variants = self._description_variants(
            normal="The hair shows enough edge detail and does not raise strong concern.",
            mild="The hair looks slightly soft in places, but the effect is not a strong warning by itself.",
            warning="Some hair areas appear blended or lacking in strand-level detail, which can be associated with generated portraits.",
            high="The hair appears very soft or painted in the visible region, making hair detail one of the stronger warning signs.",
        )
        return self._item("Hair Details", self._calibrated_score(score, overall_score), variants)

    def _teeth_detail(
        self,
        rgb: np.ndarray,
        face_signal: FaceSignal,
        overall_score: float,
    ) -> dict[str, Any]:
        if face_signal.landmarks is None or len(face_signal.landmarks) < 5:
            score = _round_score(overall_score * 0.75)
            variants = self._description_variants(
                normal="The teeth are not clearly visible, and there is no strong teeth-related concern.",
                mild="The teeth are not clear enough for a confident reading, so this is only a mild signal.",
                warning="The mouth area gives a moderate teeth-detail concern, but visibility is limited.",
                high="The mouth area raises stronger concern, although teeth visibility is still limited.",
            )
        else:
            left_mouth, right_mouth = face_signal.landmarks[3:5]
            radius = max(12, int(abs(right_mouth[0] - left_mouth[0]) * 0.48))
            region = _crop(rgb, _mouth_region(face_signal.landmarks, rgb.shape, radius))
            gray = _gray(region)
            bright_ratio = float((gray > 178).mean())
            edge_signal = _detail_anomaly(region)
            visible_teeth_signal = _clamp(bright_ratio * 220.0)
            score = _round_score((overall_score * 0.4) + (edge_signal * 0.4) + (visible_teeth_signal * 0.2))
            variants = self._description_variants(
                normal="The teeth and inner-mouth area look reasonably natural from the visible image.",
                mild="The teeth or mouth edges appear slightly soft, but not strongly suspicious.",
                warning="The teeth appear somewhat uniform or softly separated, which can suggest generated-image artifacts.",
                high="The teeth and inner-mouth area show strong uniformity or blending, making this a notable warning sign.",
            )
        return self._item("Teeth Detail", self._calibrated_score(score, overall_score), variants)

    def _lighting_consistency(
        self,
        rgb: np.ndarray,
        face_signal: FaceSignal,
        overall_score: float,
    ) -> dict[str, Any]:
        if face_signal.bbox is None:
            height, width = rgb.shape[:2]
            left_region = rgb[:, : width // 2]
            right_region = rgb[:, width // 2 :]
        else:
            x1, y1, x2, y2 = face_signal.bbox
            face = _crop(rgb, (x1, y1, x2, y2))
            _, width = face.shape[:2]
            left_region = face[:, : width // 2]
            right_region = face[:, width // 2 :]

        brightness_gap = abs(_brightness(left_region) - _brightness(right_region)) / 255.0
        lighting_signal = _clamp(brightness_gap * 420.0)
        score = _round_score((overall_score * 0.35) + (lighting_signal * 0.65))
        variants = self._description_variants(
            normal="The lighting across the face appears reasonably consistent, with no obvious lighting mismatch.",
            mild="The lighting shows small differences, but they could easily come from a normal light source.",
            warning="The face shows noticeable lighting imbalance, which can support an editing or generation signal.",
            high="The lighting looks strongly inconsistent across the face, making this a more suspicious visual signal.",
        )
        return self._item("Lighting Consistency", self._calibrated_score(score, overall_score), variants)

    def _background_complexity(
        self,
        rgb: np.ndarray,
        face_signal: FaceSignal,
        overall_score: float,
    ) -> dict[str, Any]:
        if face_signal.bbox is None:
            region = rgb
        else:
            region = rgb.copy()
            x1, y1, x2, y2 = face_signal.bbox
            if x2 > x1 and y2 > y1:
                region[y1:y2, x1:x2] = np.median(rgb.reshape(-1, 3), axis=0)

        background_signal = _detail_anomaly(region)
        score = _round_score((overall_score * 0.4) + (background_signal * 0.6))
        variants = self._description_variants(
            normal="The background looks coherent enough and does not strongly suggest generation.",
            mild="The background is slightly soft or low-detail, but this can also happen naturally with depth of field.",
            warning="The background appears vague or overly smooth in places, which can make it harder to verify as a natural scene.",
            high="The background has very limited natural detail or coherence, making it one of the stronger suspicious signals.",
        )
        return self._item("Background Coherence", self._calibrated_score(score, overall_score), variants)

    def _ear_detail(
        self,
        rgb: np.ndarray,
        face_signal: FaceSignal,
        overall_score: float,
    ) -> dict[str, Any]:
        height, width = rgb.shape[:2]
        if face_signal.bbox is None:
            side_width = max(1, width // 5)
            region = np.concatenate((rgb[:, :side_width], rgb[:, width - side_width :]), axis=1)
        else:
            x1, y1, x2, y2 = face_signal.bbox
            face_width = x2 - x1
            left = _crop(rgb, (x1 - int(face_width * 0.28), y1, x1 + int(face_width * 0.08), y2))
            right = _crop(rgb, (x2 - int(face_width * 0.08), y1, x2 + int(face_width * 0.28), y2))
            min_height = min(left.shape[0], right.shape[0])
            if min_height > 0:
                region = np.concatenate((left[:min_height], right[:min_height]), axis=1)
            else:
                region = rgb

        ear_signal = _detail_anomaly(region)
        score = _round_score((overall_score * 0.35) + (ear_signal * 0.65))
        variants = self._description_variants(
            normal="The side-face and ear area does not show a strong visible artifact.",
            mild="The ear area is a little soft or unclear, but not strongly suspicious by itself.",
            warning="The ear region appears simplified or low-detail, which can happen in generated portraits.",
            high="The ear area looks strongly simplified or soft around the edges, making it a notable warning sign.",
        )
        return self._item("Ear Detail", self._calibrated_score(score, overall_score), variants)

    def _overall_image_quality(self, rgb: np.ndarray, overall_score: float) -> dict[str, Any]:
        quality_signal = _detail_anomaly(rgb)
        score = _round_score((overall_score * 0.5) + (quality_signal * 0.5))
        variants = self._description_variants(
            normal="The image quality looks generally natural, with no strong overall polish or smoothing concern.",
            mild="The image has a slightly polished or soft look, but the overall quality is still plausible.",
            warning="The image looks unusually clean or smooth in several areas, which can support an AI-generation signal.",
            high="The image has a very polished, low-detail look overall, making quality and texture a stronger warning sign.",
        )
        return self._item("Overall Image Quality", self._calibrated_score(score, overall_score), variants)

    def _description_variants(
        self,
        normal: str,
        mild: str,
        warning: str,
        high: str,
    ) -> dict[str, str]:
        return {
            "normal": normal,
            "mild": mild,
            "warning": warning,
            "high": high,
        }

    def _pick_description(self, score: float, descriptions: dict[str, str] | str) -> str:
        if isinstance(descriptions, str):
            return descriptions
        return descriptions[_severity(score)]

    def _calibrated_score(self, score: float, overall_score: float) -> float:
        blended = (score * 0.65) + (overall_score * 0.35)
        if overall_score <= 5:
            cap = 35.0
        elif overall_score <= 15:
            cap = 45.0
        elif overall_score <= 30:
            cap = 55.0
        elif overall_score <= 50:
            cap = 70.0
        else:
            cap = 100.0
        return _round_score(min(blended, cap))

    def _item(self, title: str, score: float, descriptions: dict[str, str] | str) -> dict[str, Any]:
        rounded = _round_score(score)
        return {
            "title": title,
            "score": rounded,
            "severity": _severity(rounded),
            "description": self._pick_description(rounded, descriptions),
        }

    def _summary(
        self,
        overall_score: float,
        label: str,
        breakdown: list[dict[str, Any]],
        has_face: bool,
    ) -> str:
        strongest = sorted(breakdown, key=lambda item: item["score"], reverse=True)[:2]
        signal_names = " and ".join(item["title"].lower() for item in strongest)
        face_note = (
            " The face was clear enough for region-level checks."
            if has_face
            else " Some facial regions were not clear enough to isolate, so those items should be read as softer estimates."
        )
        verdict = "above" if label == "FAKE" else "below"
        image_type = "portrait" if has_face else "image"
        if overall_score <= 5:
            return (
                f"This {image_type} received an overall forgery score of {overall_score:.1f}%, which is "
                f"well below the current decision boundary for the returned label. The breakdown may still "
                f"note minor softness or low-detail areas, but these should not be read as strong concerns "
                f"because the model found almost no forgery evidence.{face_note}"
            )
        if overall_score <= 20:
            return (
                f"This {image_type} received an overall forgery score of {overall_score:.1f}%, which is "
                f"below the current decision boundary for the returned label. The most noticeable minor "
                f"visual notes are {signal_names}, but they are weak signals and do not outweigh the low "
                f"model score.{face_note}"
            )
        return (
            f"This {image_type} received an overall forgery score of {overall_score:.1f}%, which is {verdict} "
            f"the current decision boundary for the returned label. The most noticeable supporting signals "
            f"are {signal_names}. These observations describe visible image patterns and should be read "
            f"together with the model score, not as proof by themselves.{face_note}"
        )
