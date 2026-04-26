from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, 
    BigInteger, Float, Text, ARRAY, JSON, Index, UniqueConstraint,
    Enum, func
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
import enum
from .base import Base


class User(Base):
    """Telegram user."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lang: Mapped[str] = mapped_column(String(5), default="uz")
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bot_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    referrer_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    admin: Mapped[Optional["Admin"]] = relationship("Admin", back_populates="user", uselist=False, cascade="all, delete-orphan")
    ratings: Mapped[List["Rating"]] = relationship("Rating", back_populates="user", cascade="all, delete-orphan")
    movie_views: Mapped[List["MovieView"]] = relationship("MovieView", back_populates="user", cascade="all, delete-orphan")
    search_queries: Mapped[List["SearchQuery"]] = relationship("SearchQuery", back_populates="user", cascade="all, delete-orphan")
    channel_referrals: Mapped[List["ChannelReferral"]] = relationship("ChannelReferral", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_user_is_bot_blocked_is_banned_last_active", "is_bot_blocked", "is_banned", "last_active_at"),
        Index("ix_user_joined_at", "joined_at"),
    )


class Admin(Base):
    """Admin user with role."""
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(50))  # owner, admin, content_mgr, broadcaster
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="admin")

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_admin_user_id"),
    )


class Channel(Base):
    """Telegram channel for subscription."""
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(20))  # public, private, request_join
    invite_link: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    members_count: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    join_requests: Mapped[List["ChannelJoinRequest"]] = relationship("ChannelJoinRequest", back_populates="channel", cascade="all, delete-orphan")
    referrals: Mapped[List["ChannelReferral"]] = relationship("ChannelReferral", back_populates="channel", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_channel_is_required", "is_required"),
    )


class ChannelJoinRequest(Base):
    """Join request approval tracking."""
    __tablename__ = "channel_join_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id", ondelete="CASCADE"))
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    channel: Mapped["Channel"] = relationship("Channel", back_populates="join_requests")

    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", name="uq_channel_join_request"),
    )


class ChannelReferral(Base):
    """Track user joins via referral."""
    __tablename__ = "channel_referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id", ondelete="CASCADE"))
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="channel_referrals")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="referrals")


class Movie(Base):
    """Movie/Video content."""
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    genres: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # in seconds
    video_file_id: Mapped[str] = mapped_column(String(255))
    views: Mapped[int] = mapped_column(Integer, default=0)
    rating_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    views_list: Mapped[List["MovieView"]] = relationship("MovieView", back_populates="movie", cascade="all, delete-orphan")
    ratings: Mapped[List["Rating"]] = relationship("Rating", back_populates="movie", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_movie_year_views", "year", "views"),
    )


class MovieView(Base):
    """Track movie views."""
    __tablename__ = "movie_views"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id", ondelete="CASCADE"))
    viewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="movie_views")
    movie: Mapped["Movie"] = relationship("Movie", back_populates="views_list")

    __table_args__ = (
        Index("ix_movie_view_user_viewed_at", "user_id", "viewed_at"),
    )


class Series(Base):
    """TV Series content."""
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    genres: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    rating_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    seasons: Mapped[List["Season"]] = relationship("Season", back_populates="series", cascade="all, delete-orphan")
    ratings: Mapped[List["Rating"]] = relationship("Rating", back_populates="series", cascade="all, delete-orphan")


class Season(Base):
    """Series season."""
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(Integer, ForeignKey("series.id", ondelete="CASCADE"))
    season_number: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    series: Mapped["Series"] = relationship("Series", back_populates="seasons")
    episodes: Mapped[List["Episode"]] = relationship("Episode", back_populates="season", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("series_id", "season_number", name="uq_season_number"),
    )


class Episode(Base):
    """Series episode."""
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id", ondelete="CASCADE"))
    episode_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    video_file_id: Mapped[str] = mapped_column(String(255))
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    season: Mapped["Season"] = relationship("Season", back_populates="episodes")

    __table_args__ = (
        UniqueConstraint("season_id", "episode_number", name="uq_episode_number"),
    )


class Rating(Base):
    """User rating for movie/series."""
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=True)
    series_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("series.id", ondelete="CASCADE"), nullable=True)
    value: Mapped[int] = mapped_column(Integer)  # 1-5 stars
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="ratings")
    movie: Mapped[Optional["Movie"]] = relationship("Movie", back_populates="ratings")
    series: Mapped[Optional["Series"]] = relationship("Series", back_populates="ratings")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_rating_user_movie"),
        UniqueConstraint("user_id", "series_id", name="uq_rating_user_series"),
    )


class SearchQuery(Base):
    """Track search queries for analytics."""
    __tablename__ = "search_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    query: Mapped[str] = mapped_column(String(255))
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    searched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="search_queries")

    __table_args__ = (
        Index("ix_search_query_user_searched_at", "user_id", "searched_at"),
    )


class Broadcast(Base):
    """Mass broadcast message."""
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)  # Reference to Admin user
    status: Mapped[str] = mapped_column(String(20))  # draft, running, paused, completed, failed
    mode: Mapped[str] = mapped_column(String(20))  # copy, forward, custom
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_photo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # file_id
    media_video: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    media_animation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    media_audio: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    media_voice: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    media_document: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    buttons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # JSONB: { "type": "inline", "rows": [...] }
    segment: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # JSONB: { "lang": "uz", "active_days": 7 }
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, default=0)
    target_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_broadcast_status_updated_at", "status", "updated_at"),
    )


class Setting(Base):
    """Global settings."""
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Comment(Base):
    """User comment on movie/series."""
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=True)
    series_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("series.id", ondelete="CASCADE"), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    tg_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User")
    movie: Mapped[Optional["Movie"]] = relationship("Movie")
    series: Mapped[Optional["Series"]] = relationship("Series")

    __table_args__ = (
        Index("ix_comment_movie_approved", "movie_id", "is_approved"),
    )


class Ad(Base):
    """Advertisement/promotion."""
    __tablename__ = "ads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    buttons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    clicks_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
