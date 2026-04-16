import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _resolve_upload_dir() -> str:
    raw_dir = (os.getenv("UPLOAD_DIR") or "").strip()
    candidate = raw_dir or os.path.join(BASE_DIR, "uploads")
    if os.path.isabs(candidate):
        return os.path.abspath(candidate)
    return os.path.abspath(os.path.join(BASE_DIR, candidate))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "paper_reader")
    DEFAULT_TARGET_LANG = os.getenv("DEFAULT_TARGET_LANG", "zh-CN")
    ACCESS_TOKEN_EXPIRE_SECONDS = int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", "604800"))
    EMAIL_CODE_EXPIRE_MINUTES = int(os.getenv("EMAIL_CODE_EXPIRE_MINUTES", "10"))
    EMAIL_CODE_COOLDOWN_SECONDS = int(os.getenv("EMAIL_CODE_COOLDOWN_SECONDS", "60"))
    ALLOW_DEBUG_EMAIL_CODE = os.getenv("ALLOW_DEBUG_EMAIL_CODE", "true").lower() == "true"
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    DEMO_ACCOUNT_ENABLED = os.getenv("DEMO_ACCOUNT_ENABLED", "true").lower() == "true"
    DEMO_ACCOUNT_USERNAME = os.getenv("DEMO_ACCOUNT_USERNAME", "111")
    DEMO_ACCOUNT_PASSWORD = os.getenv("DEMO_ACCOUNT_PASSWORD", "111")
    DEMO_ACCOUNT_EMAIL = os.getenv("DEMO_ACCOUNT_EMAIL", "111@example.local")
    UPLOAD_DIR = _resolve_upload_dir()
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(50 * 1024 * 1024)))
    OCR_LAYOUT_ENABLED_DEFAULT = os.getenv("OCR_LAYOUT_ENABLED_DEFAULT", "false").lower() == "true"
    OCR_LAYOUT_LANG = os.getenv("OCR_LAYOUT_LANG", "en")
    OCR_LAYOUT_USE_GPU = os.getenv("OCR_LAYOUT_USE_GPU", "false").lower() == "true"
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
