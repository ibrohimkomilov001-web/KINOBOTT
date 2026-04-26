from enum import Enum


class SettingKey(str, Enum):
    """Setting keys for the database."""
    
    FORCE_SUBSCRIPTION = "force_subscription"
    MAINTENANCE_MODE = "maintenance_mode"
    ALLOW_PAID_BROADCAST = "allow_paid_broadcast"
    BROADCAST_BOT_RATE = "broadcast_bot_rate"
    BROADCAST_USERBOT_RATE = "broadcast_userbot_rate"
    AUTO_CODE = "auto_code"
    BASE_CHANNEL_ID = "base_channel_id"
    NEXT_MOVIE_CODE = "next_movie_code"
    NEXT_SERIES_CODE = "next_series_code"


class AdminRole(str, Enum):
    """Admin role levels."""
    
    OWNER = "owner"
    ADMIN = "admin"
    CONTENT_MGR = "content_mgr"
    BROADCASTER = "broadcaster"
    
    @property
    def permissions(self) -> list[str]:
        """Get permissions for this role."""
        if self == AdminRole.OWNER:
            return ["all"]
        elif self == AdminRole.ADMIN:
            return ["manage_content", "manage_channels", "manage_admins", "broadcast", "stats", "backup"]
        elif self == AdminRole.CONTENT_MGR:
            return ["manage_content", "stats"]
        elif self == AdminRole.BROADCASTER:
            return ["broadcast"]
        return []


class BroadcastStatus(str, Enum):
    """Broadcast status."""
    
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class BroadcastMode(str, Enum):
    """Broadcast mode (how to send)."""
    
    COPY = "copy"  # Copy message from base channel
    FORWARD = "forward"  # Forward from base channel (userbot)
    CUSTOM = "custom"  # Custom text + media


class ChannelType(str, Enum):
    """Channel type."""
    
    PUBLIC = "public"
    PRIVATE = "private"
    REQUEST_JOIN = "request_join"
