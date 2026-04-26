from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, distinct
from datetime import datetime, timedelta
from db import models
from typing import List, Tuple


class StatsRepository:
    """Repository for Stats/Analytics operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_total_users(self) -> int:
        """Get total users count."""
        stmt = select(func.count(distinct(models.User.id)))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_active_users_today(self) -> int:
        """Get users active today."""
        today = datetime.utcnow().date()
        stmt = select(func.count(distinct(models.User.id))).where(
            func.date(models.User.last_active_at) == today
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_active_users_week(self) -> int:
        """Get users active in last 7 days."""
        since = datetime.utcnow() - timedelta(days=7)
        stmt = select(func.count(distinct(models.User.id))).where(
            models.User.last_active_at >= since
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_active_users_month(self) -> int:
        """Get users active in last 30 days."""
        since = datetime.utcnow() - timedelta(days=30)
        stmt = select(func.count(distinct(models.User.id))).where(
            models.User.last_active_at >= since
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_new_users_today(self) -> int:
        """Get new users today."""
        today = datetime.utcnow().date()
        stmt = select(func.count(models.User.id)).where(
            func.date(models.User.joined_at) == today
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_new_users_week(self) -> int:
        """Get new users in last 7 days."""
        since = datetime.utcnow() - timedelta(days=7)
        stmt = select(func.count(models.User.id)).where(
            models.User.joined_at >= since
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_new_users_month(self) -> int:
        """Get new users in last 30 days."""
        since = datetime.utcnow() - timedelta(days=30)
        stmt = select(func.count(models.User.id)).where(
            models.User.joined_at >= since
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_top_movies(self, limit: int = 10) -> List[Tuple[str, int, float]]:
        """Get top movies by views."""
        stmt = select(
            models.Movie.title,
            models.Movie.views,
            models.Movie.rating_avg
        ).order_by(desc(models.Movie.views)).limit(limit)
        result = await self.session.execute(stmt)
        return result.all()

    async def get_top_series(self, limit: int = 10) -> List[Tuple[str, int, float]]:
        """Get top series by views."""
        stmt = select(
            models.Series.title,
            models.Series.views,
            models.Series.rating_avg
        ).order_by(desc(models.Series.views)).limit(limit)
        result = await self.session.execute(stmt)
        return result.all()

    async def get_top_search_queries(self, limit: int = 20) -> List[Tuple[str, int]]:
        """Get top search queries."""
        stmt = select(
            models.SearchQuery.query,
            func.count(models.SearchQuery.id).label("count")
        ).group_by(models.SearchQuery.query).order_by(desc("count")).limit(limit)
        result = await self.session.execute(stmt)
        return result.all()

    async def get_top_searches(self, limit: int = 20) -> List[Tuple[str, int]]:
        """Alias for get_top_search_queries."""
        return await self.get_top_search_queries(limit=limit)

    async def log_search_query(self, user_id: int, query: str, results_count: int) -> models.SearchQuery:
        """Log a search query."""
        search = models.SearchQuery(
            user_id=user_id,
            query=query,
            results_count=results_count
        )
        self.session.add(search)
        await self.session.flush()
        return search

    async def get_movies_count(self) -> int:
        """Get total movies count."""
        stmt = select(func.count(models.Movie.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_series_count(self) -> int:
        """Get total series count."""
        stmt = select(func.count(models.Series.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_users_by_language(self) -> dict:
        """Get user count by language."""
        stmt = select(
            models.User.lang,
            func.count(models.User.id).label("count")
        ).group_by(models.User.lang)
        result = await self.session.execute(stmt)
        return {lang: count for lang, count in result.all()}

    async def get_banned_users_count(self) -> int:
        """Get banned users count."""
        stmt = select(func.count(models.User.id)).where(models.User.is_banned == True)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_blocked_users_count(self) -> int:
        """Get bot-blocked users count."""
        stmt = select(func.count(models.User.id)).where(models.User.is_bot_blocked == True)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_premium_users_count(self) -> int:
        """Get premium users count."""
        stmt = select(func.count(models.User.id)).where(models.User.is_premium == True)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_new_users_by_day(self, days: int = 30) -> List[Tuple[str, int]]:
        """Get new users count by day (last N days)."""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = select(
            func.date(models.User.joined_at).label("date"),
            func.count(models.User.id).label("count")
        ).where(models.User.joined_at >= since).group_by("date").order_by("date")
        result = await self.session.execute(stmt)
        return result.all()

    async def get_active_users_by_day(self, days: int = 30) -> List[Tuple[str, int]]:
        """Get active users count by day (last N days)."""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = select(
            func.date(models.User.last_active_at).label("date"),
            func.count(distinct(models.User.id)).label("count")
        ).where(models.User.last_active_at >= since).group_by("date").order_by("date")
        result = await self.session.execute(stmt)
        return result.all()

    async def get_referral_stats(self) -> dict:
        """Get overall referral stats."""
        # Total referrals
        stmt = select(func.count(models.User.id)).where(models.User.referrer_id.isnot(None))
        result = await self.session.execute(stmt)
        total_referrals = result.scalar() or 0

        # Total channel referrals
        stmt = select(func.count(models.ChannelReferral.id))
        result = await self.session.execute(stmt)
        total_channel_joins = result.scalar() or 0

        return {
            "total_referrals": total_referrals,
            "total_channel_joins": total_channel_joins,
        }

    async def get_broadcast_stats(self) -> dict:
        """Get broadcast statistics."""
        stmt = select(
            func.count(models.Broadcast.id).label("total"),
            func.sum(models.Broadcast.sent_count).label("total_sent"),
            func.sum(models.Broadcast.failed_count).label("total_failed"),
            func.sum(models.Broadcast.blocked_count).label("total_blocked"),
        )
        result = await self.session.execute(stmt)
        total, sent, failed, blocked = result.first()

        return {
            "total_broadcasts": total or 0,
            "total_sent": sent or 0,
            "total_failed": failed or 0,
            "total_blocked": blocked or 0,
        }
