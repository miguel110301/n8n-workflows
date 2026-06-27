"""Application configuration, loaded once from environment variables."""
import logging
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Centralized environment configuration.

    Only DATABASE_URL is enforced as required (see `validate`) because
    it's the one variable this service cannot function without. The
    WhatsApp/Claude variables are read here for convenience even though
    today's endpoints don't call those APIs directly -- n8n owns that
    side effect -- so a missing token shouldn't block this service from
    starting.
    """

    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_PHONE_ID: str = os.getenv("WHATSAPP_PHONE_ID", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Business rule: documents below this confidence are escalated to a
    # human even when every required field is technically present.
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))

    REQUIRED_VARS = ("DATABASE_URL",)

    @classmethod
    def validate(cls) -> None:
        """Fail fast at startup instead of erroring on the first request."""
        missing = [name for name in cls.REQUIRED_VARS if not getattr(cls, name)]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
