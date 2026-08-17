import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db: str = os.getenv("MONGODB_DB", "aegis")
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    email_mode: str = os.getenv("EMAIL_MODE", "mock")
    email_sender: str = os.getenv("EMAIL_SENDER", "")
    email_app_password: str = os.getenv("EMAIL_APP_PASSWORD", "")
    heartbeat_inactive_hours: int = int(os.getenv("HEARTBEAT_INACTIVE_HOURS", "48"))
    heartbeat_check_interval_hours: int = int(os.getenv("HEARTBEAT_CHECK_INTERVAL_HOURS", "1"))
    risk_threshold_warn: float = float(os.getenv("RISK_THRESHOLD_WARN", "45"))
    risk_threshold_block: float = float(os.getenv("RISK_THRESHOLD_BLOCK", "75"))


settings = Settings()