from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    model_ready: bool
    model_name: str


class ReportItem(BaseModel):
    title: str
    score: float = Field(ge=0.0, le=100.0)
    severity: str = "normal"
    description: str


class DetectionReport(BaseModel):
    image_type: str = "Portrait Photo"
    overall_forgery_score: float = Field(ge=0.0, le=100.0)
    summary: str
    breakdown: list[ReportItem]


class PredictionResponse(BaseModel):
    label: str = Field(description="REAL or FAKE")
    confidence: float = Field(ge=0.0, le=1.0)
    fake_probability: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(ge=0.0, le=1.0)
    explanation: str
    model_name: str
    heatmap_overlay: str | None = Field(
        default=None,
        description="Data URL (PNG) of Grad-CAM heatmap overlay.",
    )
    explainability_method: str = Field(
        default="grad_cam",
        description="Explainability method used to generate the overlay.",
    )
    report: DetectionReport | None = None


class SignInRequest(BaseModel):
    email: str = Field(default="", max_length=320)
    password: str = Field(default="", max_length=128)


class SignInResponse(BaseModel):
    success: bool = True
    message: str


class SignUpRequest(BaseModel):
    email: str = Field(default="", max_length=320)
    password: str = Field(default="", max_length=128)


class SignUpResponse(BaseModel):
    success: bool = True
    message: str


class GoogleAuthRequest(BaseModel):
    credential: str = Field(default="", min_length=1)


class GoogleAuthResponse(BaseModel):
    success: bool = True
    message: str
    email: str
    name: str | None = None


class ProfileAnalysisItem(BaseModel):
    created_at: str
    label: str
    fake_probability: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    model_name: str
    risk_level: str


class ProfileStats(BaseModel):
    total_scans: int = 0
    real_count: int = 0
    fake_count: int = 0
    low_risk_count: int = 0
    medium_risk_count: int = 0
    high_risk_count: int = 0
    average_forgery_score: float = Field(default=0.0, ge=0.0, le=100.0)
    last_analysis_at: str | None = None


class ProfileActivityPoint(BaseModel):
    date: str
    count: int


class UserProfileResponse(BaseModel):
    email: str
    name: str | None = None
    picture: str | None = None
    auth_provider: str = "email"
    created_at: str | None = None
    last_login_at: str | None = None
    stats: ProfileStats
    activity_by_day: list[ProfileActivityPoint]
    recent_analyses: list[ProfileAnalysisItem]

