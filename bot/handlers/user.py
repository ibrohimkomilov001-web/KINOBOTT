from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db.repositories.user_repo import UserRepository
from db.repositories.movie_repo import MovieRepository
from db.repositories.series_repo import SeriesRepository
from db.repositories.stats_repo import StatsRepository
from sqlalchemy.ext.asyncio import AsyncSession
from bot.keyboards.user import simple_menu, rating_keyboard
from db import models
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession | None = None):
    """Handle /start command with optional deep link."""
    if session is None:
        await message.answer("Xatolik: ma'lumotlar bazasi aloqasi mavjud emas.")
        return

    user_repo = UserRepository(session)

    # Check deep link (e.g. /start code_avatar2 or /start ref_123456)
    args = message.text.split(maxsplit=1)
    deep_link = args[1].strip() if len(args) > 1 else None

    # Extract referrer before creating user
    referrer_id = None
    if deep_link and deep_link.startswith("ref_"):
        try:
            referrer_id = int(deep_link.replace("ref_", ""))
        except ValueError:
            pass
        deep_link = None  # ref link is not a movie code

    db_user = await user_repo.get_or_create(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        lang=message.from_user.language_code or "uz"
    )

    # Save referrer (only for new users)
    if referrer_id and not db_user.referrer_id and referrer_id != message.from_user.id:
        db_user.referrer_id = referrer_id
    await session.commit()

    # If deep link contains a movie code, send the movie
    if deep_link:
        movie_repo = MovieRepository(session)
        movie = await movie_repo.get_by_code(deep_link)
        if movie:
            await _send_movie(message, movie, movie_repo, db_user)
            return
        # Try series code
        series_repo = SeriesRepository(session)
        series = await series_repo.get_by_code(deep_link)
        if series:
            await _send_series(message, series, series_repo)
            return

    text = (
        "🎬 <b>Kinobotga xush kelibsiz!</b>\n\n"
        "Film yoki serial qidirish uchun nom yoki kod yuboring.\n"
        "Masalan: <code>avatar</code> yoki <code>123</code>"
    )
    await message.answer(text, reply_markup=simple_menu())


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    text = (
        "📖 <b>Yordam</b>\n\n"
        "🔍 <b>Qidirish</b> — kino nomi yoki kodini yuboring\n"
        "🎬 <b>/start</b> — bosh menu\n"
        "📖 <b>/help</b> — yordam\n\n"
        "Kino kodini bilsangiz shunchaki yuboring,\n"
        "bot sizga videoni topib beradi."
    )
    await message.answer(text)


@router.message(F.text.regexp(r"^\d+$"))
async def handle_numeric_code(message: Message, session: AsyncSession | None = None, user: models.User | None = None):
    """Handle numeric movie codes like 123, 456."""
    if session is None:
        await message.answer("Xatolik: sessiya topilmadi")
        return

    code = message.text.strip()
    movie_repo = MovieRepository(session)
    movie = await movie_repo.get_by_code(code)

    if movie:
        await _send_movie(message, movie, movie_repo, user)
        return

    # Also try as series code
    series_repo = SeriesRepository(session)
    series = await series_repo.get_by_code(code)
    if series:
        await _send_series(message, series)
        return

    await message.reply("Bu kod bo'yicha hech narsa topilmadi 😕")


@router.message(F.text.startswith("/code_"))
async def handle_code_command(message: Message, session: AsyncSession | None = None, user: models.User | None = None):
    """Handle /code_XXX commands."""
    if session is None:
        await message.answer("Xatolik: sessiya topilmadi")
        return

    code = message.text.replace("/code_", "", 1).strip()
    movie_repo = MovieRepository(session)
    movie = await movie_repo.get_by_code(code)

    if movie:
        await _send_movie(message, movie, movie_repo, user)
        return

    series_repo = SeriesRepository(session)
    series = await series_repo.get_by_code(code)
    if series:
        await _send_series(message, series)
        return

    await message.reply("Kod topilmadi 😕")


@router.message(F.text)
async def handle_text(message: Message, session: AsyncSession | None = None, user: models.User | None = None):
    """Handle plain text as search query (must be LAST handler)."""
    if session is None:
        await message.answer("Xatolik: sessiya topilmadi")
        return

    query = message.text.strip()
    if not query or query.startswith("/"):
        return

    movie_repo = MovieRepository(session)
    series_repo = SeriesRepository(session)
    stats_repo = StatsRepository(session)

    # First try exact code match
    movie = await movie_repo.get_by_code(query)
    if movie:
        await _send_movie(message, movie, movie_repo, user)
        return

    # Search movies and series
    movies = await movie_repo.search(query, limit=5)
    series = await series_repo.search(query, limit=3)

    # Log search query
    results_count = len(movies) + len(series)
    if user:
        await stats_repo.log_search_query(user.id, query, results_count)

    if not movies and not series:
        await message.reply("Hech narsa topilmadi 😕")
        await session.commit()
        return

    lines = []
    if movies:
        lines.append("🎬 <b>Kinolar:</b>")
        for m in movies:
            year = f" ({m.year})" if m.year else ""
            lines.append(f"  ▪️ {m.title}{year} — /code_{m.code}")

    if series:
        lines.append("\n📺 <b>Seriallar:</b>")
        for s in series:
            year = f" ({s.year})" if s.year else ""
            lines.append(f"  ▪️ {s.title}{year} — /code_{s.code}")

    await message.answer("\n".join(lines))
    await session.commit()


async def _send_movie(message: Message, movie: models.Movie, movie_repo: MovieRepository, user: models.User | None = None):
    """Send movie video with caption and rating keyboard."""
    # Record view
    if user:
        await movie_repo.record_view(user.id, movie.id)

    rating = f"{movie.rating_avg:.1f}" if movie.rating_avg else "0"
    caption = (
        f"🎬 <b>{movie.title}</b>"
        f"{f' ({movie.year})' if movie.year else ''}\n\n"
        f"{movie.description or ''}\n\n"
        f"⭐ Reyting: {rating}/5 ({movie.rating_count} ovoz)\n"
        f"👁 Ko'rishlar: {movie.views}"
    )

    try:
        await message.answer_video(
            video=movie.video_file_id,
            caption=caption,
            reply_markup=rating_keyboard(movie.id),
        )
    except Exception as e:
        logger.error(f"Error sending video for movie {movie.id}: {e}")
        await message.reply("Kechirasiz, videoni yuborishda xato yuz berdi.")


async def _send_series(message: Message, series, series_repo: SeriesRepository | None = None):
    """Send series info with season/episode buttons."""
    rating = f"{series.rating_avg:.1f}" if series.rating_avg else "0"
    genres = ", ".join(series.genres) if series.genres else "—"
    text = (
        f"📺 <b>{series.title}</b>"
        f"{f' ({series.year})' if series.year else ''}\n\n"
        f"{series.description or ''}\n\n"
        f"<i>Janrlar:</i> {genres}\n"
        f"⭐ Reyting: {rating}/5 ({series.rating_count} ovoz)\n"
        f"👁 Ko'rishlar: {series.views}"
    )
    kb = None
    if series_repo:
        seasons = await series_repo.get_seasons(series.id)
        if seasons:
            builder = InlineKeyboardBuilder()
            for sn in seasons:
                builder.row(InlineKeyboardButton(
                    text=f"📂 Sezon {sn.season_number}",
                    callback_data=f"user_season:{series.id}:{sn.id}"
                ))
            kb = builder.as_markup()
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("user_season:"))
async def cb_user_season(call: CallbackQuery, session: AsyncSession | None = None):
    """Show episodes for a season."""
    if not session:
        return await call.answer()
    parts = call.data.split(":")
    series_id, season_id = int(parts[1]), int(parts[2])
    repo = SeriesRepository(session)
    episodes = await repo.get_episodes(season_id)
    if not episodes:
        return await call.answer("Epizodlar topilmadi", show_alert=True)
    builder = InlineKeyboardBuilder()
    for ep in episodes:
        title = ep.title or f"Epizod {ep.episode_number}"
        builder.row(InlineKeyboardButton(
            text=f"▶️ {ep.episode_number}. {title}",
            callback_data=f"user_ep:{ep.id}"
        ))
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"user_series_back:{series_id}"))
    await call.message.edit_reply_markup(reply_markup=builder.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("user_ep:"))
async def cb_user_episode(call: CallbackQuery, session: AsyncSession | None = None):
    """Send episode video."""
    if not session:
        return await call.answer()
    from sqlalchemy import select
    ep_id = int(call.data.split(":")[1])
    result = await session.execute(select(models.Episode).where(models.Episode.id == ep_id))
    ep = result.scalars().first()
    if not ep:
        return await call.answer("Epizod topilmadi", show_alert=True)
    title = ep.title or f"Epizod {ep.episode_number}"
    try:
        await call.message.answer_video(
            video=ep.video_file_id,
            caption=f"📺 {title}"
        )
    except Exception as e:
        logger.error(f"Error sending episode {ep_id}: {e}")
        await call.answer("Video yuborishda xatolik", show_alert=True)
    await call.answer()


@router.callback_query(F.data.startswith("user_series_back:"))
async def cb_user_series_back(call: CallbackQuery, session: AsyncSession | None = None):
    """Go back to season list."""
    if not session:
        return await call.answer()
    series_id = int(call.data.split(":")[1])
    repo = SeriesRepository(session)
    seasons = await repo.get_seasons(series_id)
    builder = InlineKeyboardBuilder()
    for sn in seasons:
        builder.row(InlineKeyboardButton(
            text=f"📂 Sezon {sn.season_number}",
            callback_data=f"user_season:{series_id}:{sn.id}"
        ))
    await call.message.edit_reply_markup(reply_markup=builder.as_markup())
    await call.answer()
