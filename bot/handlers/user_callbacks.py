from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.enums import ChatMemberStatus
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.movie_repo import MovieRepository
from db.repositories.channel_repo import ChannelRepository
from db.repositories.stats_repo import StatsRepository
from bot.states import CommentSG
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


# ─── Series rating callback ─────────────────────────────────────────────────
@router.callback_query(F.data.startswith("rate_s:"))
async def handle_series_rate(call: CallbackQuery, session: AsyncSession | None = None, user: models.User | None = None):
    """Handle series rating."""
    try:
        _, series_id_str, value_str = call.data.split(":")
        series_id = int(series_id_str)
        value = int(value_str)
    except Exception:
        await call.answer("Noma'lum format", show_alert=True)
        return

    if not session or not user:
        await call.answer("Xatolik", show_alert=True)
        return

    from db.repositories.series_repo import SeriesRepository
    from sqlalchemy import select

    stmt = select(models.Rating).where(models.Rating.user_id == user.id, models.Rating.series_id == series_id)
    result = await session.execute(stmt)
    existing = result.scalars().first()

    if existing:
        existing.value = value
    else:
        rating = models.Rating(user_id=user.id, series_id=series_id, value=value)
        session.add(rating)

    series_repo = SeriesRepository(session)
    await series_repo.update_rating(series_id)
    await session.commit()

    await call.answer(f"Rahmat! Siz {value} ⭐ berdingiz.")


# ─── Referral info callback ─────────────────────────────────────────────────
@router.callback_query(F.data == "my_referral")
async def handle_my_referral(call: CallbackQuery, session: AsyncSession | None = None, user: models.User | None = None):
    if not session or not user:
        return await call.answer("Xatolik", show_alert=True)
    from db.repositories.user_repo import UserRepository
    repo = UserRepository(session)
    stats = await repo.get_referral_stats(user.id)
    bot_info = await call.bot.me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"
    text = (
        f"🔗 <b>Referral</b>\n\n"
        f"Sizning havolangiz:\n<code>{link}</code>\n\n"
        f"👥 Taklif qilganlar: {stats['referral_count']}"
    )
    await call.message.answer(text)
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


# ─── Comment callback ─────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("comment:"))
async def handle_comment_start(call: CallbackQuery, state: FSMContext):
    """Start comment writing flow."""
    parts = call.data.split(":")
    content_type = parts[1]  # movie or series
    content_id = int(parts[2])
    await state.update_data(comment_type=content_type, comment_content_id=content_id)
    await call.message.answer("💬 Kommentingizni yozing (500 belgigacha):")
    await state.set_state(CommentSG.text)
    await call.answer()


@router.message(CommentSG.text)
async def handle_comment_text(message: Message, state: FSMContext, session: AsyncSession | None = None, user: models.User | None = None):
    """Save user comment and send to admin group for moderation."""
    if not session or not user:
        await message.reply("❌ Xatolik")
        await state.clear()
        return

    text = (message.text or "").strip()
    if not text or len(text) > 500:
        await message.reply("❌ Komment 1-500 belgi bo'lishi kerak. Qayta yozing:")
        return

    data = await state.get_data()
    content_type = data.get("comment_type")
    content_id = data.get("comment_content_id")

    comment = models.Comment(
        user_id=user.id,
        movie_id=content_id if content_type == "movie" else None,
        series_id=content_id if content_type == "series" else None,
        text=text,
        is_approved=False,
        tg_message_id=message.message_id,
    )
    session.add(comment)
    await session.commit()

    # Send to admin group for moderation
    from config import settings
    group_id = settings.COMMENT_GROUP_ID
    if group_id:
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            content_label = "🎬 Kino" if content_type == "movie" else "📺 Serial"
            username = f"@{user.username}" if user.username else f"ID:{user.id}"
            mod_text = (
                f"💬 <b>Yangi komment</b>\n\n"
                f"👤 {user.first_name} ({username})\n"
                f"{content_label} ID: {content_id}\n\n"
                f"<i>{text}</i>"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"cmt_approve:{comment.id}"),
                    InlineKeyboardButton(text="❌ Rad etish", callback_data=f"cmt_reject:{comment.id}"),
                ]
            ])
            await message.bot.send_message(group_id, mod_text, reply_markup=kb)
        except Exception as e:
            logger.error(f"Failed to send comment to group: {e}")

    await message.reply("✅ Kommentingiz qabul qilindi! Admin tasdiqlashini kuting.")
    await state.clear()


# ─── Comment moderation callbacks (admin group) ───────────────────────────
@router.callback_query(F.data.startswith("cmt_approve:"))
async def handle_comment_approve(call: CallbackQuery, session: AsyncSession | None = None):
    """Admin approves a comment."""
    if not session:
        return await call.answer("Sessiya yo'q", show_alert=True)
    cmt_id = int(call.data.split(":")[1])
    from sqlalchemy import select
    result = await session.execute(select(models.Comment).where(models.Comment.id == cmt_id))
    comment = result.scalars().first()
    if not comment:
        return await call.answer("Komment topilmadi", show_alert=True)
    comment.is_approved = True
    await session.commit()
    await call.message.edit_text(
        call.message.text + f"\n\n✅ <b>Tasdiqlandi</b> ({call.from_user.first_name})",
    )
    await call.answer("✅ Tasdiqlandi")


@router.callback_query(F.data.startswith("cmt_reject:"))
async def handle_comment_reject(call: CallbackQuery, session: AsyncSession | None = None):
    """Admin rejects and deletes a comment."""
    if not session:
        return await call.answer("Sessiya yo'q", show_alert=True)
    cmt_id = int(call.data.split(":")[1])
    from sqlalchemy import select
    result = await session.execute(select(models.Comment).where(models.Comment.id == cmt_id))
    comment = result.scalars().first()
    if not comment:
        return await call.answer("Komment topilmadi", show_alert=True)
    await session.delete(comment)
    await session.commit()
    await call.message.edit_text(
        call.message.text + f"\n\n❌ <b>Rad etildi</b> ({call.from_user.first_name})",
    )
    await call.answer("❌ Rad etildi")
