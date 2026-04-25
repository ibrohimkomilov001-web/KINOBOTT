from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

    # Bot Configuration
    BOT_TOKEN: str
    BOT_USERNAME: str
    SUPER_ADMIN_IDS: list[int]

    # Database - optional, will be built from plugin vars if available
    DATABASE_URL: Optional[str] = None
    PGHOST: Optional[str] = None
    PGPORT: Optional[int] = None
    PGUSER: Optional[str] = None
    PGPASSWORD: Optional[str] = None
    PGDATABASE: Optional[str] = None

    # Redis
    REDIS_URL: Optional[str] = None
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: int = 6379

    # Userbot (Pyrogram) - Optional
    API_ID: Optional[int] = None
    API_HASH: Optional[str] = None
    USERBOT_SESSION_STRING: Optional[str] = None

    # Telegram Channels/Groups
    BASE_CHANNEL_ID: Optional[int] = None
    LOG_CHANNEL_ID: Optional[int] = None
    COMMENT_GROUP_ID: Optional[int] = None

    # Broadcast Settings
    BROADCAST_BOT_RATE: int = 28  # requests per second
    BROADCAST_USERBOT_RATE: int = 20  # requests per second
    ALLOW_PAID_BROADCAST: bool = False

    # Logging & Other
    LOG_LEVEL: str = "INFO"
    TZ: str = "Asia/Tashkent"

    # Feature Flags
    FORCE_SUBSCRIPTION: bool = True
    MAINTENANCE_MODE: bool = False

    @field_validator("API_ID", "BASE_CHANNEL_ID", "LOG_CHANNEL_ID", "COMMENT_GROUP_ID", mode="before")
    @classmethod
    def parse_optional_int(cls, v):
        """Convert empty strings to None for optional int fields."""
        if v is None or v == "" or v == "0":
            return None
        return v

    @field_validator("API_HASH", "USERBOT_SESSION_STRING", mode="before")
    @classmethod
    def parse_optional_str(cls, v):
        """Convert empty strings to None for optional string fields."""
        if v is None or v == "":
            return None
        return v

    @field_validator("SUPER_ADMIN_IDS", mode="before")
    @classmethod
    def parse_super_admin_ids(cls, v: str | list[int]) -> list[int]:
        """Parse comma-separated admin IDs."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",")]
        return []

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Convert DATABASE_URL to async PostgreSQL URL if needed."""
        if not self.DATABASE_URL:
            logger.error("DATABASE_URL is not set!")
            raise ValueError("DATABASE_URL environment variable is required but not set")
        
        url = self.DATABASE_URL
        
        # Fix localhost to postgres service name in Railway
        if "localhost" in url:
            logger.warning("Detected localhost in DATABASE_URL, converting to Railway service name")
            url = url.replace("localhost", "postgres")
        
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Log the async URL (without credentials for security)
        safe_url = url.split("@")[-1] if "@" in url else url
        logger.info(f"Using database URL: {safe_url}")
        
        return url

    def has_userbot(self) -> bool:
        """Check if userbot credentials are configured."""
        return bool(
            self.API_ID
            and self.API_HASH
            and self.USERBOT_SESSION_STRING
        )

    @property
    def FIXED_REDIS_URL(self) -> Optional[str]:
        """Fix localhost in REDIS_URL for Railway environment."""
        url = self.REDIS_URL
        if not url:
            return None
        if "localhost" in url:
            logger.warning("Detected localhost in REDIS_URL, converting to Railway service name")
            url = url.replace("localhost", "redis")
        return url


# Global settings instance
settings = Settings()
