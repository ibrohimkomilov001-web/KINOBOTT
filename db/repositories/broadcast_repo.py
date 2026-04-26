from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime
from db import models
from db.constants import BroadcastStatus
from typing import Optional, List


class BroadcastRepository:
    """Repository for Broadcast operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, admin_id: int, status: str = BroadcastStatus.DRAFT.value,
                     mode: str = "custom") -> models.Broadcast:
        """Create a new broadcast."""
        broadcast = models.Broadcast(
            admin_id=admin_id,
            status=status,
            mode=mode
        )
        self.session.add(broadcast)
        await self.session.flush()
        return broadcast

    async def get_by_id(self, broadcast_id: int) -> Optional[models.Broadcast]:
        """Get broadcast by ID."""
        stmt = select(models.Broadcast).where(models.Broadcast.id == broadcast_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[models.Broadcast]:
        """Get all broadcasts."""
        stmt = select(models.Broadcast).order_by(desc(models.Broadcast.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_recent(self, limit: int = 20) -> List[models.Broadcast]:
        """Get recent broadcasts (alias for get_all sorted by recency)."""
        return await self.get_all(limit=limit)

    async def get_by_status(self, status: str, limit: int = 100) -> List[models.Broadcast]:
        """Get broadcasts by status."""
        stmt = select(models.Broadcast).where(
            models.Broadcast.status == status
        ).order_by(desc(models.Broadcast.updated_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_running(self) -> List[models.Broadcast]:
        """Get running broadcasts."""
        return await self.get_by_status(BroadcastStatus.RUNNING.value)

    async def get_drafts(self, admin_id: int) -> List[models.Broadcast]:
        """Get draft broadcasts for admin."""
        stmt = select(models.Broadcast).where(
            models.Broadcast.status == BroadcastStatus.DRAFT.value,
            models.Broadcast.admin_id == admin_id
        ).order_by(desc(models.Broadcast.created_at))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def start_broadcast(self, broadcast_id: int, target_count: int) -> Optional[models.Broadcast]:
        """Start a broadcast."""
        broadcast = await self.get_by_id(broadcast_id)
        if broadcast:
            broadcast.status = BroadcastStatus.RUNNING.value
            broadcast.started_at = datetime.utcnow()
            broadcast.target_count = target_count
            await self.session.flush()
        return broadcast

    async def pause_broadcast(self, broadcast_id: int) -> Optional[models.Broadcast]:
        """Pause a broadcast."""
        broadcast = await self.get_by_id(broadcast_id)
        if broadcast:
            broadcast.status = BroadcastStatus.PAUSED.value
            await self.session.flush()
        return broadcast

    async def resume_broadcast(self, broadcast_id: int) -> Optional[models.Broadcast]:
        """Resume a paused broadcast."""
        broadcast = await self.get_by_id(broadcast_id)
        if broadcast:
            broadcast.status = BroadcastStatus.RUNNING.value
            await self.session.flush()
        return broadcast

    async def complete_broadcast(self, broadcast_id: int) -> Optional[models.Broadcast]:
        """Complete a broadcast."""
        broadcast = await self.get_by_id(broadcast_id)
        if broadcast:
            broadcast.status = BroadcastStatus.COMPLETED.value
            broadcast.completed_at = datetime.utcnow()
            await self.session.flush()
        return broadcast

    async def fail_broadcast(self, broadcast_id: int) -> Optional[models.Broadcast]:
        """Mark broadcast as failed."""
        broadcast = await self.get_by_id(broadcast_id)
        if broadcast:
            broadcast.status = BroadcastStatus.FAILED.value
            broadcast.completed_at = datetime.utcnow()
            await self.session.flush()
        return broadcast

    async def increment_sent(self, broadcast_id: int) -> int:
        """Increment sent count."""
        broadcast = await self.get_by_id(broadcast_id)
        if broadcast:
            broadcast.sent_count += 1
            await self.session.flush()
            return broadcast.sent_count
        return 0

    async def increment_failed(self, broadcast_id: int) -> int:
        """Increment failed count."""
        broadcast = await self.get_by_id(broadcast_id)
        if broadcast:
            broadcast.failed_count += 1
            await self.session.flush()
            return broadcast.failed_count
        return 0

    async def increment_blocked(self, broadcast_id: int) -> int:
        """Increment blocked count."""
        broadcast = await self.get_by_id(broadcast_id)
        if broadcast:
            broadcast.blocked_count += 1
            await self.session.flush()
            return broadcast.blocked_count
        return 0

    async def update_counts(self, broadcast_id: int, sent: int = 0, failed: int = 0, blocked: int = 0) -> Optional[models.Broadcast]:
        """Update broadcast counts."""
        broadcast = await self.get_by_id(broadcast_id)
        if broadcast:
            broadcast.sent_count = sent
            broadcast.failed_count = failed
            broadcast.blocked_count = blocked
            await self.session.flush()
        return broadcast

    async def update(self, broadcast_id: int, **kwargs) -> Optional[models.Broadcast]:
        """Update broadcast."""
        broadcast = await self.get_by_id(broadcast_id)
        if broadcast:
            for key, value in kwargs.items():
                if hasattr(broadcast, key):
                    setattr(broadcast, key, value)
            broadcast.updated_at = datetime.utcnow()
            await self.session.flush()
        return broadcast

    async def get_total_count(self) -> int:
        """Get total broadcast count."""
        stmt = select(func.count(models.Broadcast.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def delete(self, broadcast_id: int) -> bool:
        """Delete broadcast."""
        broadcast = await self.get_by_id(broadcast_id)
        if broadcast:
            await self.session.delete(broadcast)
            await self.session.flush()
            return True
        return False
