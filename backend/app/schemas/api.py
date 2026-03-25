from pydantic import BaseModel, EmailStr, Field


class RegisterResponse(BaseModel):
    user_id: int
    email: EmailStr
    full_name: str
    profile_id: int | None = None
    profile_source_type: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    user_id: int
    email: EmailStr
    full_name: str
    profile_exists: bool = False
    profile_id: int | None = None
    profile_source_type: str | None = None


class RunAnalysisRequest(BaseModel):
    user_id: int


class SelectInfluencersRequest(BaseModel):
    user_id: int
    influencer_ids: list[int]


class GenerateStrategyRequest(BaseModel):
    user_id: int


class GeneratePostRequest(BaseModel):
    user_id: int
    topic: str
    objective: str = "engagement"
    media_context: str | None = None


class NotificationSettingsRequest(BaseModel):
    user_id: int
    outlook_email: EmailStr
    enabled: bool = True
    cadence_days: int = Field(default=3, ge=1, le=14)
    preferred_hour: int = Field(default=9, ge=0, le=23)
    timezone: str = Field(default="UTC", min_length=2, max_length=64)
    preferred_weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])


class NotificationSettingsResponse(BaseModel):
    user_id: int
    outlook_email: EmailStr
    enabled: bool
    cadence_days: int
    preferred_hour: int
    timezone: str
    preferred_weekdays: list[int]


class SendNotificationRequest(BaseModel):
    user_id: int
    force_send: bool = False


class InfluencerOut(BaseModel):
    id: int
    name: str
    profile_link: str
    description: str
    rank_score: int
    selected: bool


class GapRowOut(BaseModel):
    category: str
    user: str
    influencer: str
    gap: str
    recommendation: str
