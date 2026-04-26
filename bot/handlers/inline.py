"""Inline query handler — kino va serial qidirish inline rejimda."""

from aiogram import Router
from aiogram.types import (
    InlineQuery, InlineQueryResultArticle, InlineQueryResultVideo,
    InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton,
)
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.movie_repo import MovieRepository
from db.repositories.series_repo import SeriesRepository
import hashlib
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.inline_query()
async def inline_search(query: InlineQuery, session: AsyncSession | None = None):
    """Handle inline queries — search movies and series."""
    text = (query.query or "").strip()
    results = []

    if not session:
        await query.answer(results, cache_time=5, is_personal=True)
        return

    movie_repo = MovieRepository(session)
    series_repo = SeriesRepository(session)

    if not text:
        # Bo'sh so'rov — top kinolar
        movies = await movie_repo.get_top(limit=10)
        for m in movies:
            results.append(_movie_to_result(m))
        await query.answer(results, cache_time=30, is_personal=False,
                           switch_pm_text="🎬 Botga o'tish", switch_pm_parameter="start")
        return

    # Avval kod bo'yicha qidirish
    movie = await movie_repo.get_by_code(text)
    if movie:
        results.append(_movie_to_result(movie))

    series = await series_repo.get_by_code(text)
    if series:
        results.append(_series_to_result(series))

    # Keyin nom bo'yicha qidirish
    if len(results) < 10:
        movies = await movie_repo.search(text, limit=10 - len(results))
        existing_ids = {r.id for r in results}
        for m in movies:
            rid = f"m_{m.id}"
            if rid not in existing_ids:
                results.append(_movie_to_result(m))

    if len(results) < 15:
        series_list = await series_repo.search(text, limit=5)
        existing_ids = {r.id for r in results}
        for s in series_list:
            rid = f"s_{s.id}"
            if rid not in existing_ids:
                results.append(_series_to_result(s))

    await query.answer(
        results[:50],
        cache_time=10,
        is_personal=False,
        switch_pm_text="🎬 Botga o'tish",
        switch_pm_parameter="start",
    )


def _movie_to_result(movie) -> InlineQueryResultArticle:
    """Convert movie to inline result."""
    rating = f"{movie.rating_avg:.1f}" if movie.rating_avg else "0"
    year = f" ({movie.year})" if movie.year else ""
    desc = movie.description or ""
    if len(desc) > 100:
        desc = desc[:100] + "..."

    text = (
        f"🎬 <b>{movie.title}</b>{year}\n\n"
        f"{movie.description or ''}\n\n"
        f"⭐ {rating}/5 | 👁 {movie.views} ko'rish\n"
        f"Kod: <code>{movie.code}</code>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Ko'rish", url=f"https://t.me/share/url?url=/code_{movie.code}")],
    ])

    return InlineQueryResultArticle(
        id=f"m_{movie.id}",
        title=f"🎬 {movie.title}{year}",
        description=f"⭐ {rating} | 👁 {movie.views} | Kod: {movie.code}",
        thumbnail_url=None,
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="HTML",
        ),
        reply_markup=kb,
    )


def _series_to_result(series) -> InlineQueryResultArticle:
    """Convert series to inline result."""
    rating = f"{series.rating_avg:.1f}" if series.rating_avg else "0"
    year = f" ({series.year})" if series.year else ""
    genres = ", ".join(series.genres) if series.genres else ""

    text = (
        f"📺 <b>{series.title}</b>{year}\n\n"
        f"{series.description or ''}\n\n"
        f"🎭 {genres}\n"
        f"⭐ {rating}/5 | 👁 {series.views} ko'rish\n"
        f"Kod: <code>{series.code}</code>"
    )

    return InlineQueryResultArticle(
        id=f"s_{series.id}",
        title=f"📺 {series.title}{year}",
        description=f"⭐ {rating} | {genres} | Kod: {series.code}",
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="HTML",
        ),
    )
