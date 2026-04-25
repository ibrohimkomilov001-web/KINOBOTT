"""FSM handlers for stateful conversations."""

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.movie_repo import MovieRepository
from db.repositories.series_repo import SeriesRepository
from db.repositories.channel_repo import ChannelRepository
from db.repositories.broadcast_repo import BroadcastRepository
from db.repositories.admin_repo import AdminRepository
from db.repositories.user_repo import UserRepository
from db.constants import AdminRole
from bot.states import AddMovieSG, AddSeriesSG, AddChannelSG, BroadcastSG
from bot.keyboards.admin import confirm_kb
import logging

logger = logging.getLogger(__name__)
router = Router()


# ════════════════════════════════════════════════════════════════════════════
# Movie FSM
# ════════════════════════════════════════════════════════════════════════════

@router.message(AddMovieSG.title)
async def movie_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.reply("Kino kodini kiriting (masalan: avatar2):")
    await state.set_state(AddMovieSG.code)


@router.message(AddMovieSG.code)
async def movie_code(message: Message, state: FSMContext, session: AsyncSession | None = None):
    code = message.text.lower().strip()
    if session:
        movie_repo = MovieRepository(session)
        existing = await movie_repo.get_by_code(code)
        if existing:
            await message.reply(f"Kod '{code}' allaqachon mavjud. Boshqa kod kiriting:")
            return
    await state.update_data(code=code)
    await message.reply("Janrlarni kiriting (vergul bilan ajratib):")
    await state.set_state(AddMovieSG.genres)


@router.message(AddMovieSG.genres)
async def movie_genres(message: Message, state: FSMContext):
    genres = [g.strip() for g in message.text.split(",")]
    await state.update_data(genres=genres)
    await message.reply("Yilni kiriting:")
    await state.set_state(AddMovieSG.year)


@router.message(AddMovieSG.year)
async def movie_year(message: Message, state: FSMContext):
    try:
        year = int(message.text)
        await state.update_data(year=year)
        await message.reply("Video faylni yuklang:")
        await state.set_state(AddMovieSG.video)
    except ValueError:
        await message.reply("Yil raqam bo'lishi kerak:")


@router.message(AddMovieSG.video)
async def movie_video(message: Message, state: FSMContext, session: AsyncSession | None = None):
    if not message.video:
        await message.reply("Video fayl yuklang:")
        return

    data = await state.get_data()

    if session:
        movie_repo = MovieRepository(session)
        movie = await movie_repo.create(
            code=data["code"],
            title=data["title"],
            video_file_id=message.video.file_id,
            genres=data.get("genres"),
            year=data.get("year"),
        )
        await session.commit()

        await message.reply(
            f"✅ Kino qo'shildi!\n\n"
            f"Nomi: {movie.title}\n"
            f"Kodi: {movie.code}\n"
            f"Yili: {movie.year}"
        )

    await state.clear()


# ════════════════════════════════════════════════════════════════════════════
# Series FSM
# ════════════════════════════════════════════════════════════════════════════

@router.message(AddSeriesSG.title)
async def series_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.reply("Serial kodini kiriting (masalan: got):")
    await state.set_state(AddSeriesSG.code)


@router.message(AddSeriesSG.code)
async def series_code(message: Message, state: FSMContext, session: AsyncSession | None = None):
    code = message.text.lower().strip()
    if session:
        series_repo = SeriesRepository(session)
        existing = await series_repo.get_by_code(code)
        if existing:
            await message.reply(f"Kod '{code}' allaqachon mavjud. Boshqa kod kiriting:")
            return
    await state.update_data(code=code)
    await message.reply("Janrlarni kiriting (vergul bilan ajratib):")
    await state.set_state(AddSeriesSG.genres)


@router.message(AddSeriesSG.genres)
async def series_genres(message: Message, state: FSMContext):
    genres = [g.strip() for g in message.text.split(",")]
    await state.update_data(genres=genres)
    await message.reply("Yilni kiriting:")
    await state.set_state(AddSeriesSG.year)


@router.message(AddSeriesSG.year)
async def series_year(message: Message, state: FSMContext, session: AsyncSession | None = None):
    try:
        year = int(message.text)
    except ValueError:
        await message.reply("Yil raqam bo'lishi kerak:")
        return

    data = await state.get_data()

    if session:
        series_repo = SeriesRepository(session)
        series = await series_repo.create(
            code=data["code"],
            title=data["title"],
            genres=data.get("genres"),
            year=year,
        )
        await session.commit()

        await message.reply(
            f"✅ Serial qo'shildi!\n\n"
            f"Nomi: {series.title}\n"
            f"Kodi: {series.code}\n"
            f"Yili: {series.year}\n\n"
            f"Sezon qo'shish uchun /admin panelidan foydalaning."
        )

    await state.clear()


# ════════════════════════════════════════════════════════════════════════════
# Channel FSM
# ════════════════════════════════════════════════════════════════════════════

@router.message(AddChannelSG.tg_chat_id)
async def channel_chat_id(message: Message, state: FSMContext):
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.reply("Chat ID raqam bo'lishi kerak (masalan: -1001234567890):")
        return
    await state.update_data(tg_chat_id=chat_id)
    await message.reply("Kanal nomini kiriting:")
    await state.set_state(AddChannelSG.title)


@router.message(AddChannelSG.title)
async def channel_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Public", callback_data="ch_type_public"),
            InlineKeyboardButton(text="Private", callback_data="ch_type_private"),
        ],
        [InlineKeyboardButton(text="Request Join", callback_data="ch_type_request_join")],
    ])
    await message.reply("Kanal turini tanlang:", reply_markup=kb)
    await state.set_state(AddChannelSG.channel_type)


@router.callback_query(F.data.startswith("ch_type_"), AddChannelSG.channel_type)
async def channel_type_selected(call, state: FSMContext):
    channel_type = call.data.replace("ch_type_", "")
    await state.update_data(channel_type=channel_type)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha", callback_data="ch_required_yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="ch_required_no"),
        ]
    ])
    await call.message.answer("Bu kanal majburiy obuna uchunmi?", reply_markup=kb)
    await state.set_state(AddChannelSG.is_required)
    await call.answer()


@router.callback_query(F.data.startswith("ch_required_"), AddChannelSG.is_required)
async def channel_required_selected(call, state: FSMContext, session: AsyncSession | None = None):
    is_required = call.data == "ch_required_yes"
    data = await state.get_data()

    if session:
        channel_repo = ChannelRepository(session)
        existing = await channel_repo.get_by_tg_chat_id(data["tg_chat_id"])
        if existing:
            await call.message.answer(f"Bu kanal allaqachon mavjud: {existing.title}")
            await state.clear()
            await call.answer()
            return

        channel = await channel_repo.create(
            tg_chat_id=data["tg_chat_id"],
            title=data["title"],
            channel_type=data["channel_type"],
            is_required=is_required,
        )
        await session.commit()

        req_text = "Ha" if is_required else "Yo'q"
        await call.message.answer(
            f"✅ Kanal qo'shildi!\n\n"
            f"Nomi: {channel.title}\n"
            f"ID: {channel.tg_chat_id}\n"
            f"Turi: {channel.type}\n"
            f"Majburiy: {req_text}"
        )

    await state.clear()
    await call.answer()


# ════════════════════════════════════════════════════════════════════════════
# Broadcast FSM
# ════════════════════════════════════════════════════════════════════════════

@router.message(BroadcastSG.text)
async def broadcast_text(message: Message, state: FSMContext, session: AsyncSession | None = None):
    """Receive broadcast text or media."""
    text = message.text or message.caption or ""
    media_data = {}

    if message.photo:
        media_data["media_photo"] = message.photo[-1].file_id
    elif message.video:
        media_data["media_video"] = message.video.file_id
    elif message.document:
        media_data["media_document"] = message.document.file_id
    elif message.animation:
        media_data["media_animation"] = message.animation.file_id

    await state.update_data(text=text, **media_data)

    if session:
        user_repo = UserRepository(session)
        target_count = await user_repo.get_total_count()
    else:
        target_count = "?"

    preview = f"📢 <b>Broadcast ko'rik</b>\n\n{text}\n\n👥 Maqsad: ~{target_count} foydalanuvchi"
    if media_data:
        media_type = list(media_data.keys())[0].replace("media_", "")
        preview += f"\n📎 Media: {media_type}"

    await message.answer(preview, reply_markup=confirm_kb("broadcast"))
    await state.set_state(BroadcastSG.confirm)


@router.callback_query(F.data == "broadcast_confirm", BroadcastSG.confirm)
async def broadcast_confirm(call, state: FSMContext, session: AsyncSession | None = None):
    """Confirm and start broadcast."""
    if not session:
        await call.answer("Sessiya topilmadi", show_alert=True)
        return

    data = await state.get_data()
    broadcast_repo = BroadcastRepository(session)

    bc = await broadcast_repo.create(admin_id=call.from_user.id, mode="custom")
    bc.text = data.get("text")
    bc.media_photo = data.get("media_photo")
    bc.media_video = data.get("media_video")
    bc.media_document = data.get("media_document")
    bc.media_animation = data.get("media_animation")
    await session.commit()

    await call.message.edit_text(f"✅ Broadcast #{bc.id} yaratildi va ishga tushirilmoqda...")
    await call.answer()
    await state.clear()

    # Start broadcast in background
    import asyncio
    from services.broadcaster import BroadcastEngine
    from bot.loader import bot

    engine = BroadcastEngine(session, bot)
    asyncio.create_task(engine.start(bc.id, call.from_user.id))


@router.callback_query(F.data == "broadcast_cancel", BroadcastSG.confirm)
async def broadcast_cancel(call, state: FSMContext):
    """Cancel broadcast creation."""
    await state.clear()
    await call.message.edit_text("❌ Broadcast bekor qilindi.")
    await call.answer()
