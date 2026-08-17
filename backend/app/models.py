from datetime import datetime, timezone

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    google_id: str
    email: EmailStr
    name: str
    parent_email: EmailStr
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime | None = None
    alert_email_sent_for_inactive: bool = False


class ChatMessage(BaseModel):
    sender_id: str
    recipient_id: str
    text: str
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClassificationResult(BaseModel):
    toxicity: float = 0.0
    toxicity_label: str = "neutral"
    intent: str = "neutral"
    risk_score: float = 0.0
    reason: str = ""
    model: str = ""


class Decision(BaseModel):
    action: str  # deliver | warn | block
    risk_score: float
    reason: str


class AlertRecord(BaseModel):
    alert_type: str  # received_toxic | sent_improper | app_inactive
    user_id: str
    parent_email: EmailStr
    message_text: str = ""
    sender_name: str = ""
    reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))