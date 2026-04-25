"""Backup and restore service."""

import asyncio
import json
import gzip
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.channel_repo import ChannelRepository
from db.repositories.settings_repo import SettingsRepository
from db.repositories.admin_repo import AdminRepository
from db.repositories.movie_repo import MovieRepository
from db.repositories.series_repo import SeriesRepository
import logging

logger = logging.getLogger(__name__)


class BackupService:
    """Service for backup and restore operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)

    async def backup_now(self) -> Optional[str]:
        """Create a backup file now."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_data = await self._export_data()
            
            backup_file = self.backup_dir / f"kinobot_backup_{timestamp}.json.gz"
            
            # Compress and save
            with gzip.open(backup_file, 'wt') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            logger.info(f"Backup created: {backup_file}")
            return str(backup_file)
        
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None

    async def _export_data(self) -> dict:
        """Export data to JSON."""
        channel_repo = ChannelRepository(self.session)
        settings_repo = SettingsRepository(self.session)
        admin_repo = AdminRepository(self.session)

        channels = await channel_repo.get_all()
        settings = await settings_repo.get_all()
        admins = await admin_repo.get_all_admins()

        return {
            "exported_at": datetime.utcnow().isoformat(),
            "channels": [
                {
                    "tg_chat_id": c.tg_chat_id,
                    "title": c.title,
                    "type": c.type,
                    "invite_link": c.invite_link,
                    "is_required": c.is_required,
                }
                for c in channels
            ],
            "settings": settings,
            "admins": [
                {
                    "user_id": a.user_id,
                    "role": a.role,
                }
                for a in admins
            ],
        }

    async def restore(self, backup_file: str) -> bool:
        """Restore from a backup file."""
        try:
            backup_path = Path(backup_file)
            
            # Read and decompress
            with gzip.open(backup_path, 'rt') as f:
                data = json.load(f)
            
            channel_repo = ChannelRepository(self.session)
            settings_repo = SettingsRepository(self.session)
            admin_repo = AdminRepository(self.session)

            # Restore channels
            for ch_data in data.get("channels", []):
                existing = await channel_repo.get_by_tg_chat_id(ch_data["tg_chat_id"])
                if not existing:
                    await channel_repo.create(
                        tg_chat_id=ch_data["tg_chat_id"],
                        title=ch_data["title"],
                        channel_type=ch_data["type"],
                        invite_link=ch_data.get("invite_link"),
                        is_required=ch_data.get("is_required", False),
                    )

            # Restore settings
            for key, value in data.get("settings", {}).items():
                await settings_repo.set(key, value)

            # Restore admins (careful: don't overwrite existing)
            for admin_data in data.get("admins", []):
                existing = await admin_repo.get_by_user_id(admin_data["user_id"])
                if not existing:
                    await admin_repo.create(admin_data["user_id"], admin_data["role"])

            await self.session.commit()
            logger.info(f"Restore completed from {backup_file}")
            return True
        
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            await self.session.rollback()
            return False

