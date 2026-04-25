from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.enums import ChatMemberStatus
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.movie_repo import MovieRepository
from db.repositories.channel_repo import ChannelRepository
from db.repositories.stats_repo import StatsRepository
from db import models
import logging

logger = logging.getLogger(__name__)
router = Router()


# ─── Subscription check callback ────────────────────────────────────────────
@router.callback_query(F.data == "check_subscription")
async def handle_check_subscription(call: CallbackQuery, session: AsyncSession | None = None):
    """User pressed 'Tekshirish' after subscribing."""
    if not session:
        await call.answer("Xatolik", show_alert=True)
        return

    from bot.loader import bot

    channel_repo = ChannelRepository(session)
    required = await channel_repo.get_required_channels()

    ok_statuses = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
    not_subscribed = []

    for ch in required:
        try:
            member = await bot.get_chat_member(ch.tg_chat_id, call.from_user.id)
            if member.status not in ok_statuses:
                not_subscribed.append(ch)
        except Exception:
            not_subscribed.append(ch)

    if not_subscribed:
        names = ", ".join(ch.title for ch in not_subscribed)
        await call.answer(f"Hali obuna bo'lmagan kanallar: {names}", show_alert=True)
    else:
        await call.message.edit_text("✅ Obuna tasdiqlandi! Endi botdan foydalanishingiz mumkin.")
        await call.answer("Muvaffaqiyatli! ✅")


# ─── Rating callback ────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("rate:"))
async def handle_rate(call: CallbackQuery, session: AsyncSession | None = None, user: models.User | None = None):
    """Handle movie rating."""
    try:
        _, movie_id_str, value_str = call.data.split(":")
        movie_id = int(movie_id_str)
        value = int(value_str)
    except Exception:
        await call.answer("Noma'lum format", show_alert=True)
        return

    if not session or not user:
        await call.answer("Xatolik: sessiya yoki foydalanuvchi topilmadi", show_alert=True)
        return

    movie_repo = MovieRepository(session)

    from sqlalchemy import select
    stmt = select(models.Rating).where(models.Rating.user_id == user.id, models.Rating.movie_id == movie_id)
    result = await session.execute(stmt)
    existing = result.scalars().first()

    if existing:
        existing.value = value
    else:
        rating = models.Rating(user_id=user.id, movie_id=movie_id, value=value)
        session.add(rating)

    await movie_repo.update_rating(movie_id)
    await session.commit()

    await call.answer(f"Rahmat! Siz {value} ⭐ berdingiz.")


# ─── Top movies callback ────────────────────────────────────────────────────
@router.callback_query(F.data == "top_movies")
async def handle_top_movies(call: CallbackQuery, session: AsyncSession | None = None):
    if not session:
        await call.answer("Xatolik: sessiya topilmadi", show_alert=True)
        return

    stats = StatsRepository(session)
    top = await stats.get_top_movies(limit=10)
    if not top:
        await call.answer("Top kinolar topilmadi", show_alert=True)
        return

    lines = ["🔝 <b>Top kinolar:</b>\n"]
    for i, t in enumerate(top):
        rating = f"{t[2]:.1f}" if t[2] else "0"
        lines.append(f"  {i+1}. {t[0]} — {t[1]} ko'rish — ⭐{rating}")

    await call.message.answer("\n".join(lines))
    await call.answer()


# ─── Random movies callback ─────────────────────────────────────────────────
@router.callback_query(F.data == "random")
async def handle_random(call: CallbackQuery, session: AsyncSession | None = None):
    if not session:
        await call.answer("Xatolik: sessiya topilmadi", show_alert=True)
        return

    movie_repo = MovieRepository(session)
    objs = await movie_repo.get_random(limit=3)
    if not objs:
        await call.answer("Hech narsa topilmadi", show_alert=True)
        return

    lines = ["🎲 <b>Tasodifiy kinolar:</b>\n"]
    for m in objs:
        year = f" ({m.year})" if m.year else ""
        lines.append(f"  ▪️ {m.title}{year} — /code_{m.code}")

    await call.message.answer("\n".join(lines))
    await call.answer()
