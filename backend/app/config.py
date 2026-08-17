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
    model_dir: str = os.getenv("MODEL_DIR", os.path.join(os.path.dirname(__file__), "..", "models"))
    qwen_model_path: str = os.getenv("QWEN_MODEL_PATH", os.path.join(model_dir, "Qwen2.5-1.5B-Instruct"))
    toxic_bert_path: str = os.getenv("TOXIC_BERT_PATH", os.path.join(model_dir, "toxic-bert"))
    use_llm: bool = os.getenv("USE_LLM", "true").lower() == "true"
    lora_adapter_path: str = os.getenv("LORA_ADAPTER_PATH", os.path.join(model_dir, "lora-aegis"))
    use_lora: bool = os.getenv("USE_LORA", "false").lower() == "true"
    cascade: bool = os.getenv("CASCADE", "true").lower() == "true"
    llm_trigger_toxicity: float = float(os.getenv("LLM_TRIGGER_TOXICITY", "0.35"))
    qwen_max_new_tokens: int = int(os.getenv("QWEN_MAX_NEW_TOKENS", "56"))
    qwen_max_input_tokens: int = int(os.getenv("QWEN_MAX_INPUT_TOKENS", "256"))


settings = Settings()