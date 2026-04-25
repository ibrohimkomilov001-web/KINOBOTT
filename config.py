from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import logging
import os

# Setup basic logging to see environment info
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Log ALL environment variables for debugging
logger.info("=" * 80)
logger.info("ALL Environment Variables:")
for key in sorted(os.environ.keys()):
    value = os.environ[key]
    # Hide sensitive values
    if any(x in key.upper() for x in ['PASSWORD', 'TOKEN', 'SECRET', 'PASS', 'KEY', 'CREDENTIAL']):
        value = '***HIDDEN***' if len(value) > 0 else value
    if len(value) < 200:
        logger.info(f"  {key}={value}")
    else:
        logger.info(f"  {key}={value[:100]}...{value[-50:]}")
logger.info("=" * 80)


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

    # Database
    DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Userbot (Pyrogram) - Optional
    API_ID: Optional[int] = None
    API_HASH: Optional[str] = None
    USERBOT_SESSION_STRING: Optional[str] = None

    # Telegram Channels/Groups
    BASE_CHANNEL_ID: int
    LOG_CHANNEL_ID: int
    COMMENT_GROUP_ID: int

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
    def FIXED_REDIS_URL(self) -> str:
        """Fix localhost in REDIS_URL for Railway environment."""
        url = self.REDIS_URL
        if "localhost" in url:
            logger.warning("Detected localhost in REDIS_URL, converting to Railway service name")
            url = url.replace("localhost", "redis")
            logger.info(f"Using Redis URL: {url}")
        return url


# Global settings instance
settings = Settings()
