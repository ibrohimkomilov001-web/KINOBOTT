from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
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

    # Check deep link (e.g. /start code_avatar2)
    args = message.text.split(maxsplit=1)
    deep_link = args[1].strip() if len(args) > 1 else None

    db_user = await user_repo.get_or_create(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        lang=message.from_user.language_code or "uz"
    )
    await session.commit()

    # If deep link contains a movie code, send the movie
    if deep_link:
        movie_repo = MovieRepository(session)
        movie = await movie_repo.get_by_code(deep_link)
        if movie:
            await _send_movie(message, movie, movie_repo, db_user)
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


async def _send_series(message: Message, series):
    """Send series info."""
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
    await message.answer(text)
