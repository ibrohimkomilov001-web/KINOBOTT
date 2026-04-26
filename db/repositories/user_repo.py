from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from datetime import datetime, timedelta
from db import models
from typing import Optional, List


class UserRepository:
    """Repository for User operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, username: Optional[str] = None, 
                     first_name: Optional[str] = None, lang: str = "uz",
                     referrer_id: Optional[int] = None) -> models.User:
        """Create a new user."""
        user = models.User(
            id=user_id,
            username=username,
            first_name=first_name,
            lang=lang,
            referrer_id=referrer_id
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: int) -> Optional[models.User]:
        """Get user by ID."""
        stmt = select(models.User).where(models.User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_or_create(self, user_id: int, **kwargs) -> models.User:
        """Get existing user or create new one."""
        user = await self.get_by_id(user_id)
        if not user:
            user = await self.create(user_id, **kwargs)
        return user

    async def update_last_active(self, user_id: int) -> Optional[models.User]:
        """Update user last_active_at timestamp."""
        user = await self.get_by_id(user_id)
        if user:
            user.last_active_at = datetime.utcnow()
            await self.session.flush()
        return user

    async def ban_user(self, user_id: int) -> Optional[models.User]:
        """Ban a user."""
        user = await self.get_by_id(user_id)
        if user:
            user.is_banned = True
            await self.session.flush()
        return user

    async def unban_user(self, user_id: int) -> Optional[models.User]:
        """Unban a user."""
        user = await self.get_by_id(user_id)
        if user:
            user.is_banned = False
            await self.session.flush()
        return user

    async def mark_blocked(self, user_id: int) -> Optional[models.User]:
        """Mark user as bot blocked."""
        user = await self.get_by_id(user_id)
        if user:
            user.is_bot_blocked = True
            await self.session.flush()
        return user

    async def unmark_blocked(self, user_id: int) -> Optional[models.User]:
        """Unmark user as bot blocked."""
        user = await self.get_by_id(user_id)
        if user:
            user.is_bot_blocked = False
            await self.session.flush()
        return user

    async def get_total_count(self) -> int:
        """Get total user count."""
        stmt = select(func.count(models.User.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_active_users_today(self) -> int:
        """Get users active today."""
        today = datetime.utcnow().date()
        stmt = select(func.count(models.User.id)).where(
            func.date(models.User.last_active_at) == today
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_banned_count(self) -> int:
        """Get banned user count."""
        stmt = select(func.count(models.User.id)).where(models.User.is_banned == True)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_blocked_count(self) -> int:
        """Get bot-blocked user count."""
        stmt = select(func.count(models.User.id)).where(models.User.is_bot_blocked == True)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_new_users_count(self, days: int = 1) -> int:
        """Get new users in last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = select(func.count(models.User.id)).where(models.User.joined_at >= since)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_premium_users_count(self) -> int:
        """Get premium users count."""
        stmt = select(func.count(models.User.id)).where(models.User.is_premium == True)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_users_by_language(self, lang: str, limit: int = 1000, offset: int = 0) -> List[models.User]:
        """Get users by language."""
        stmt = select(models.User).where(
            models.User.lang == lang
        ).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_referral_stats(self, user_id: int) -> dict:
        """Get referral stats for a user."""
        # Count direct referrals
        stmt = select(func.count(models.User.id)).where(models.User.referrer_id == user_id)
        result = await self.session.execute(stmt)
        referral_count = result.scalar() or 0

        # Get referral joins
        stmt = select(func.count(models.ChannelReferral.id)).where(
            models.ChannelReferral.user_id == user_id
        )
        result = await self.session.execute(stmt)
        channel_joins = result.scalar() or 0

        return {
            "referral_count": referral_count,
            "channel_joins": channel_joins,
        }

    async def get_active_users_since(self, days: int = 7) -> List[models.User]:
        """Get users active in last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = select(models.User).where(
            models.User.last_active_at >= since,
            models.User.is_banned == False
        ).order_by(desc(models.User.last_active_at))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    def _apply_segment_filters(self, query, segment: Optional[dict]):
        """Apply segment filters to a SQLAlchemy query (shared by ID list and count)."""
        if not segment or not isinstance(segment, dict):
            return query

        seg_type = segment.get("type", "all")

        # Simple segment types
        if seg_type == "premium":
            query = query.where(models.User.is_premium == True)
        elif seg_type == "active":
            days = int(segment.get("days", 7))
            since = datetime.utcnow() - timedelta(days=days)
            query = query.where(models.User.last_active_at >= since)
        elif seg_type == "new":
            days = int(segment.get("days", 7))
            since = datetime.utcnow() - timedelta(days=days)
            query = query.where(models.User.joined_at >= since)
        elif seg_type == "active_7":
            since = datetime.utcnow() - timedelta(days=7)
            query = query.where(models.User.last_active_at >= since)
        elif seg_type == "active_30":
            since = datetime.utcnow() - timedelta(days=30)
            query = query.where(models.User.last_active_at >= since)

        # Custom multi-AND filters
        if segment.get("active_days"):
            since = datetime.utcnow() - timedelta(days=int(segment["active_days"]))
            query = query.where(models.User.last_active_at >= since)
        if segment.get("new_days"):
            since = datetime.utcnow() - timedelta(days=int(segment["new_days"]))
            query = query.where(models.User.joined_at >= since)
        if segment.get("lang"):
            query = query.where(models.User.lang == segment["lang"])
        if segment.get("joined_after"):
            joined_after = datetime.fromisoformat(segment["joined_after"])
            query = query.where(models.User.joined_at >= joined_after)
        if segment.get("premium_only"):
            query = query.where(models.User.is_premium == True)
        if segment.get("non_premium"):
            query = query.where(models.User.is_premium == False)

        return query

    async def get_users_for_broadcast(self, segment: Optional[dict] = None, limit: int = 100000, offset: int = 0) -> List[int]:
        """Get user IDs for broadcast based on segment filter."""
        query = select(models.User.id).where(
            models.User.is_banned == False,
            models.User.is_bot_blocked == False
        )
        query = self._apply_segment_filters(query, segment)
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_for_broadcast(self, segment: Optional[dict] = None) -> int:
        """Count users matching the segment for real-time target preview."""
        query = select(func.count(models.User.id)).where(
            models.User.is_banned == False,
            models.User.is_bot_blocked == False
        )
        query = self._apply_segment_filters(query, segment)
        result = await self.session.execute(query)
        return result.scalar() or 0
