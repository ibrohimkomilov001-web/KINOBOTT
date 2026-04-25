from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


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
    DATABASE_URL: str

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
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    def has_userbot(self) -> bool:
        """Check if userbot credentials are configured."""
        return bool(
            self.API_ID
            and self.API_HASH
            and self.USERBOT_SESSION_STRING
        )


# Global settings instance
settings = Settings()
