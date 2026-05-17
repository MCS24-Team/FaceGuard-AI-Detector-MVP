from __future__ import annotations

import logging

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from .core.settings_loader import load_settings
from .schemas import (
    GoogleAuthRequest,
    GoogleAuthResponse,
    HealthResponse,
    PredictionResponse,
    SignInRequest,
    SignInResponse,
    SignUpRequest,
    SignUpResponse,
    UserProfileResponse,
)
from .services.auth_service import AuthService
from .services.model_service import model_service_from_settings
from .services.preprocessing import crop_largest_face, image_to_tensor, strip_exif_and_load_image, validate_upload
from .services.report_service import ReportService


settings = load_settings()
logger = logging.getLogger(__name__)
model_service = model_service_from_settings(settings)
report_service = ReportService(enabled=settings.enable_detection_report)
auth_service = AuthService(
    enabled=settings.enable_database,
    database_url=settings.database_url,
    database_name=settings.database_name,
    users_collection=settings.users_collection,
)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FaceGuard MVP backend for local prototype demonstration.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.frontend_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    try:
        model_service.ensure_loaded()
    except Exception:
        # Allow app startup so /api/health can report model readiness.
        return


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        model_ready=model_service.model_ready,
        model_name=settings.model_name,
    )


@app.post("/api/auth/signin", response_model=SignInResponse)
def sign_in(payload: SignInRequest) -> SignInResponse:
    email = payload.email.strip()
    password = payload.password

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    success, message, status_code = auth_service.authenticate(
        email=email,
        password=password,
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=message)

    return SignInResponse(success=True, message=message)


@app.post("/api/auth/signup", response_model=SignUpResponse)
def sign_up(payload: SignUpRequest) -> SignUpResponse:
    email = payload.email.strip()
    password = payload.password

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    success, message, status_code = auth_service.register(
        email=email,
        password=password,
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=message)

    return SignUpResponse(success=True, message=message)


@app.post("/api/auth/google", response_model=GoogleAuthResponse)
def google_auth(payload: GoogleAuthRequest) -> GoogleAuthResponse:
    if not settings.google_client_id:
        raise HTTPException(
            status_code=503,
            detail="Google sign-in is not configured. Set FACEGUARD_GOOGLE_CLIENT_ID.",
        )

    try:
        claims = google_id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid Google sign-in token.") from exc

    if not claims.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account email is not verified.")

    email = str(claims.get("email") or "").strip()
    google_sub = str(claims.get("sub") or "").strip()
    name = claims.get("name")
    picture = claims.get("picture")

    success, message, status_code = auth_service.authenticate_google_user(
        email=email,
        google_sub=google_sub,
        name=str(name) if name else None,
        picture=str(picture) if picture else None,
    )

    if not success:
        raise HTTPException(status_code=status_code, detail=message)

    return GoogleAuthResponse(success=True, message=message, email=email, name=name)


@app.get("/api/profile", response_model=UserProfileResponse)
def get_profile(email: str) -> UserProfileResponse:
    success, payload, status_code = auth_service.get_user_profile(email=email)
    if not success:
        raise HTTPException(status_code=status_code, detail=payload)
    return UserProfileResponse(**payload)


@app.post("/api/analyze", response_model=PredictionResponse)
def analyze_image(
    file: UploadFile = File(...),
    email: str | None = Form(default=None),
) -> PredictionResponse:
    try:
        model_service.ensure_loaded()

        raw = validate_upload(
            upload=file,
            allowed_mime_types=settings.allowed_mime_types,
            max_upload_bytes=settings.max_upload_bytes,
        )
        image = strip_exif_and_load_image(raw)
        inference_image = crop_largest_face(
            image=image,
            enabled=settings.enable_face_crop,
            margin=settings.face_crop_margin,
        )
        tensor = image_to_tensor(
            image=inference_image,
            image_size=model_service.image_size,
            device=model_service.device,
            mean=model_service.mean,
            std=model_service.std,
        )

        result = model_service.predict(image_tensor=tensor, source_image=inference_image)
        report = report_service.build_report(
            image=image,
            fake_probability=result.fake_probability,
            label=result.label,
        )
        if email:
            auth_service.record_analysis_result(
                email=email,
                label=result.label,
                fake_probability=result.fake_probability,
                confidence=result.confidence,
                model_name=result.model_name,
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Image analysis failed.")
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {exc.__class__.__name__}") from exc

    return PredictionResponse(
        label=result.label,
        confidence=result.confidence,
        fake_probability=result.fake_probability,
        threshold=result.threshold,
        explanation=result.explanation,
        model_name=result.model_name,
        heatmap_overlay=result.heatmap_overlay,
        explainability_method=result.explainability_method,
        report=report,
    )


@app.exception_handler(HTTPException)
def http_exception_handler(_, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

