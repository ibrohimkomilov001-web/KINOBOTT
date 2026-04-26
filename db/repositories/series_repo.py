from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_, Integer
from datetime import datetime
from db import models
from typing import Optional, List


class SeriesRepository:
    """Repository for Series operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, code: str, title: str, description: Optional[str] = None,
                     genres: Optional[List[str]] = None, year: Optional[int] = None) -> models.Series:
        """Create a new series."""
        series = models.Series(
            code=code,
            title=title,
            description=description,
            genres=genres,
            year=year
        )
        self.session.add(series)
        await self.session.flush()
        return series

    async def get_by_id(self, series_id: int) -> Optional[models.Series]:
        """Get series by ID."""
        stmt = select(models.Series).where(models.Series.id == series_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_code(self, code: str) -> Optional[models.Series]:
        """Get series by code."""
        stmt = select(models.Series).where(models.Series.code == code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def search(self, query: str, limit: int = 10) -> List[models.Series]:
        """Search series by title or code."""
        search_term = f"%{query}%"
        stmt = select(models.Series).where(
            or_(
                models.Series.title.ilike(search_term),
                models.Series.code.ilike(search_term)
            )
        ).order_by(desc(models.Series.views)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search_by_genre(self, genre: str, limit: int = 10) -> List[models.Series]:
        """Search series by genre."""
        stmt = select(models.Series).where(
            models.Series.genres.contains([genre])
        ).order_by(desc(models.Series.views)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_random(self, limit: int = 5) -> List[models.Series]:
        """Get random series."""
        stmt = select(models.Series).order_by(func.random()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_top_series(self, limit: int = 10) -> List[models.Series]:
        """Get top series by views."""
        stmt = select(models.Series).order_by(desc(models.Series.views)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_season(self, series_id: int, season_number: int) -> models.Season:
        """Add a season to series."""
        season = models.Season(series_id=series_id, season_number=season_number)
        self.session.add(season)
        await self.session.flush()
        return season

    async def get_seasons(self, series_id: int) -> List[models.Season]:
        """Get all seasons for a series."""
        stmt = select(models.Season).where(models.Season.series_id == series_id).order_by(models.Season.season_number)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_episode(self, season_id: int, episode_number: int, video_file_id: str,
                         title: Optional[str] = None, duration: Optional[int] = None) -> models.Episode:
        """Add an episode to season."""
        episode = models.Episode(
            season_id=season_id,
            episode_number=episode_number,
            video_file_id=video_file_id,
            title=title,
            duration=duration
        )
        self.session.add(episode)
        await self.session.flush()
        return episode

    async def get_episodes(self, season_id: int) -> List[models.Episode]:
        """Get all episodes for a season."""
        stmt = select(models.Episode).where(models.Episode.season_id == season_id).order_by(models.Episode.episode_number)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def increment_views(self, series_id: int) -> int:
        """Increment series views count."""
        series = await self.get_by_id(series_id)
        if series:
            series.views += 1
            await self.session.flush()
            return series.views
        return 0

    async def get_rating_stats(self, series_id: int) -> dict:
        """Get rating stats for a series."""
        stmt = select(func.avg(models.Rating.value), func.count(models.Rating.id)).where(
            models.Rating.series_id == series_id
        )
        result = await self.session.execute(stmt)
        avg_rating, count = result.first()
        
        return {
            "rating_avg": avg_rating,
            "rating_count": count or 0,
        }

    async def update_rating(self, series_id: int) -> Optional[models.Series]:
        """Update series rating from ratings table."""
        rating_stats = await self.get_rating_stats(series_id)
        series = await self.get_by_id(series_id)
        if series:
            series.rating_avg = rating_stats["rating_avg"]
            series.rating_count = rating_stats["rating_count"]
            await self.session.flush()
        return series

    async def get_next_code(self) -> str:
        """Get next auto-increment numeric code for series."""
        stmt = select(func.max(
            func.cast(models.Series.code, Integer)
        )).where(models.Series.code.regexp_match(r'^\d+$'))
        result = await self.session.execute(stmt)
        max_code = result.scalar()
        return str((max_code or 0) + 1)

    async def get_total_count(self) -> int:
        """Get total series count."""
        stmt = select(func.count(models.Series.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_all_paginated(self, page: int = 0, per_page: int = 10):
        """Get paginated series + total pages."""
        total = await self.get_total_count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        stmt = (select(models.Series)
                .order_by(desc(models.Series.id))
                .offset(page * per_page).limit(per_page))
        result = await self.session.execute(stmt)
        return result.scalars().all(), total_pages

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[models.Series]:
        """Get all series."""
        stmt = select(models.Series).order_by(desc(models.Series.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(self, series_id: int, **kwargs) -> Optional[models.Series]:
        """Update series."""
        series = await self.get_by_id(series_id)
        if series:
            for key, value in kwargs.items():
                if hasattr(series, key):
                    setattr(series, key, value)
            series.updated_at = datetime.utcnow()
            await self.session.flush()
        return series

    async def delete(self, series_id: int) -> bool:
        """Delete series."""
        series = await self.get_by_id(series_id)
        if series:
            await self.session.delete(series)
            await self.session.flush()
            return True
        return False
