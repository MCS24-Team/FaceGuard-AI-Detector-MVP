from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=REPO_ROOT / ".env", override=False)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return default
    entries = tuple(item.strip() for item in value.split(",") if item.strip())
    return entries or default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _repo_relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


@dataclass(frozen=True)
class FaceGuardSettings:
    app_name: str = "FaceGuard MVP"
    app_version: str = "0.1.0"

    # ── Active model ─────────────────────────────────────────────
    # Uncomment ONE block below, then restart the backend.
    #
    # ViT-B/16 (currently active):
    model_name: str = os.getenv("FACEGUARD_MODEL_NAME", "vit")
    model_path: Path = _repo_relative_path(
        os.getenv(
            "FACEGUARD_MODEL_PATH",
            str(Path("models") / "baseline" / os.getenv("HF_MODEL_FILE", "vit3.pth")),
        )
    )
    #
    # Xception:
    # model_name: str = "xception"
    # model_path: Path = REPO_ROOT / "models" / "pretrained" / "xception.pth"
    #
    # PG-FDD (Fair Deepfake Detector):
    # model_name: str = "pg_fdd"
    # model_path: Path = REPO_ROOT / "models" / "pretrained" / "pg_fdd.pth"
    #
    fake_threshold: float = _env_float("FACEGUARD_FAKE_THRESHOLD", 0.25)

    # Upload policy
    max_upload_mb: int = 10
    allowed_extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp")
    allowed_mime_types: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "image/webp",
    )
    enable_face_crop: bool = _env_bool("FACEGUARD_ENABLE_FACE_CROP", False)
    face_crop_margin: float = _env_float("FACEGUARD_FACE_CROP_MARGIN", 0.35)
    enable_detection_report: bool = _env_bool("FACEGUARD_ENABLE_DETECTION_REPORT", True)

    # Frontend/backend local development
    backend_host: str = "127.0.0.1"
    backend_port: int = 8001
    frontend_origin: str = os.getenv("FACEGUARD_FRONTEND_ORIGIN", "http://localhost:5173")
    frontend_origins: tuple[str, ...] = _env_csv("FACEGUARD_FRONTEND_ORIGINS", (frontend_origin,))

    # Optional MongoDB persistence and auth settings
    enable_database: bool = _env_bool("FACEGUARD_ENABLE_DATABASE", False)
    database_url: str = os.getenv("FACEGUARD_DATABASE_URL", "mongodb://localhost:27017/faceguard")
    database_name: str = os.getenv("FACEGUARD_DATABASE_NAME", "faceguard")
    upload_collection: str = os.getenv("FACEGUARD_UPLOAD_COLLECTION", "uploads")
    users_collection: str = os.getenv("FACEGUARD_USERS_COLLECTION", "users")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


SETTINGS = FaceGuardSettings()
