from __future__ import annotations

from io import BytesIO
from typing import Iterable

from fastapi import HTTPException, UploadFile
import numpy as np
from PIL import Image, ImageOps
import torch
from torchvision import transforms


def validate_upload(upload: UploadFile, allowed_mime_types: Iterable[str], max_upload_bytes: int) -> bytes:
    if upload.content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {upload.content_type}",
        )

    raw = upload.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(raw) > max_upload_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds max allowed size of {max_upload_bytes // (1024 * 1024)} MB.",
        )

    return raw


def strip_exif_and_load_image(raw: bytes) -> Image.Image:
    # Apply EXIF orientation before stripping metadata to keep visual orientation stable.
    source = Image.open(BytesIO(raw))
    source = ImageOps.exif_transpose(source).convert("RGB")
    cleaned_buffer = BytesIO()
    source.save(cleaned_buffer, format="PNG")
    cleaned_buffer.seek(0)
    return Image.open(cleaned_buffer).convert("RGB")


def crop_largest_face(image: Image.Image, enabled: bool = True, margin: float = 0.35) -> Image.Image:
    if not enabled:
        return image

    try:
        import cv2
    except ImportError:
        return image

    rgb = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    max_dimension = max(gray.shape)
    scale = 1.0
    if max_dimension > 1000:
        scale = 1000.0 / max_dimension
        gray_for_detection = cv2.resize(
            gray,
            (int(gray.shape[1] * scale), int(gray.shape[0] * scale)),
            interpolation=cv2.INTER_AREA,
        )
    else:
        gray_for_detection = gray

    face_boxes: list[tuple[int, int, int, int]] = []
    cascade_names = (
        "haarcascade_frontalface_default.xml",
        "haarcascade_frontalface_alt2.xml",
        "haarcascade_profileface.xml",
    )

    for cascade_name in cascade_names:
        cascade_path = cv2.data.haarcascades + cascade_name
        detector = cv2.CascadeClassifier(cascade_path)
        if detector.empty():
            continue

        detected = detector.detectMultiScale(
            gray_for_detection,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(40, 40),
        )
        for x, y, width, height in detected:
            if scale != 1.0:
                x = int(x / scale)
                y = int(y / scale)
                width = int(width / scale)
                height = int(height / scale)
            face_boxes.append((x, y, width, height))

    if not face_boxes:
        return image

    x, y, width, height = max(face_boxes, key=lambda box: box[2] * box[3])
    margin = max(0.0, min(margin, 1.0))
    pad_x = int(width * margin)
    pad_y = int(height * margin)

    left = max(0, x - pad_x)
    top = max(0, y - pad_y)
    right = min(image.width, x + width + pad_x)
    bottom = min(image.height, y + height + pad_y)

    if right <= left or bottom <= top:
        return image

    return image.crop((left, top, right, bottom)).convert("RGB")


def build_inference_transform(
    image_size: int,
    mean: tuple[float, ...] = (0.485, 0.456, 0.406),
    std: tuple[float, ...] = (0.229, 0.224, 0.225),
) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=list(mean), std=list(std)),
        ]
    )


def image_to_tensor(
    image: Image.Image,
    image_size: int,
    device: torch.device,
    mean: tuple[float, ...] = (0.485, 0.456, 0.406),
    std: tuple[float, ...] = (0.229, 0.224, 0.225),
) -> torch.Tensor:
    transform = build_inference_transform(image_size=image_size, mean=mean, std=std)
    tensor = transform(image).unsqueeze(0).to(device)
    return tensor
