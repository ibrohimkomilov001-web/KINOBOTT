from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_, Integer
from datetime import datetime
from db import models
from typing import Optional, List


class MovieRepository:
    """Repository for Movie operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, code: str, title: str, video_file_id: str,
                     description: Optional[str] = None, genres: Optional[List[str]] = None,
                     year: Optional[int] = None, duration: Optional[int] = None) -> models.Movie:
        """Create a new movie."""
        movie = models.Movie(
            code=code,
            title=title,
            video_file_id=video_file_id,
            description=description,
            genres=genres,
            year=year,
            duration=duration
        )
        self.session.add(movie)
        await self.session.flush()
        return movie

    async def get_by_id(self, movie_id: int) -> Optional[models.Movie]:
        """Get movie by ID."""
        stmt = select(models.Movie).where(models.Movie.id == movie_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_code(self, code: str) -> Optional[models.Movie]:
        """Get movie by code."""
        stmt = select(models.Movie).where(models.Movie.code == code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def search(self, query: str, limit: int = 10) -> List[models.Movie]:
        """Search movies by title or description (fuzzy/full-text)."""
        # Simple ILIKE search (can be upgraded to pg_trgm full-text)
        search_term = f"%{query}%"
        stmt = select(models.Movie).where(
            or_(
                models.Movie.title.ilike(search_term),
                models.Movie.code.ilike(search_term)
            )
        ).order_by(desc(models.Movie.views)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search_by_genre(self, genre: str, limit: int = 10) -> List[models.Movie]:
        """Search movies by genre."""
        # PostgreSQL ARRAY contains
        stmt = select(models.Movie).where(
            models.Movie.genres.contains([genre])
        ).order_by(desc(models.Movie.views)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_random(self, limit: int = 5) -> List[models.Movie]:
        """Get random movies."""
        stmt = select(models.Movie).order_by(func.random()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_top_movies(self, limit: int = 10) -> List[models.Movie]:
        """Get top movies by views."""
        stmt = select(models.Movie).order_by(desc(models.Movie.views)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_year(self, year: int, limit: int = 20) -> List[models.Movie]:
        """Get movies by year."""
        stmt = select(models.Movie).where(models.Movie.year == year).order_by(desc(models.Movie.views)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def record_view(self, user_id: int, movie_id: int) -> models.MovieView:
        """Record a movie view."""
        view = models.MovieView(user_id=user_id, movie_id=movie_id)
        self.session.add(view)
        
        # Increment views count
        movie = await self.get_by_id(movie_id)
        if movie:
            movie.views += 1
        
        await self.session.flush()
        return view

    async def increment_views(self, movie_id: int) -> int:
        """Increment movie views count."""
        movie = await self.get_by_id(movie_id)
        if movie:
            movie.views += 1
            await self.session.flush()
            return movie.views
        return 0

    async def get_rating_stats(self, movie_id: int) -> dict:
        """Get rating stats for a movie."""
        stmt = select(func.avg(models.Rating.value), func.count(models.Rating.id)).where(
            models.Rating.movie_id == movie_id
        )
        result = await self.session.execute(stmt)
        avg_rating, count = result.first()
        
        return {
            "rating_avg": avg_rating,
            "rating_count": count or 0,
        }

    async def update_rating(self, movie_id: int) -> Optional[models.Movie]:
        """Update movie rating from ratings table."""
        # Get average rating
        rating_stats = await self.get_rating_stats(movie_id)
        movie = await self.get_by_id(movie_id)
        if movie:
            movie.rating_avg = rating_stats["rating_avg"]
            movie.rating_count = rating_stats["rating_count"]
            await self.session.flush()
        return movie

    async def get_next_code(self) -> str:
        """Get next auto-increment numeric code."""
        stmt = select(func.max(
            func.cast(models.Movie.code, Integer)
        )).where(models.Movie.code.regexp_match(r'^\d+$'))
        result = await self.session.execute(stmt)
        max_code = result.scalar()
        return str((max_code or 0) + 1)

    async def get_total_count(self) -> int:
        """Get total movie count."""
        stmt = select(func.count(models.Movie.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_all_paginated(self, page: int = 0, per_page: int = 10):
        """Get paginated movies + total pages."""
        total = await self.get_total_count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        stmt = (select(models.Movie)
                .order_by(desc(models.Movie.id))
                .offset(page * per_page).limit(per_page))
        result = await self.session.execute(stmt)
        return result.scalars().all(), total_pages

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[models.Movie]:
        """Get all movies."""
        stmt = select(models.Movie).order_by(desc(models.Movie.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(self, movie_id: int, **kwargs) -> Optional[models.Movie]:
        """Update movie."""
        movie = await self.get_by_id(movie_id)
        if movie:
            for key, value in kwargs.items():
                if hasattr(movie, key):
                    setattr(movie, key, value)
            movie.updated_at = datetime.utcnow()
            await self.session.flush()
        return movie

    async def delete(self, movie_id: int) -> bool:
        """Delete movie."""
        movie = await self.get_by_id(movie_id)
        if movie:
            await self.session.delete(movie)
            await self.session.flush()
            return True
        return False
