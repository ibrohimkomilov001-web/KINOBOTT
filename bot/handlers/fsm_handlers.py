"""FSM handlers for all stateful conversations."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.movie_repo import MovieRepository
from db.repositories.series_repo import SeriesRepository
from db.repositories.channel_repo import ChannelRepository
from db.repositories.broadcast_repo import BroadcastRepository
from db.repositories.admin_repo import AdminRepository
from db.repositories.user_repo import UserRepository
from db.repositories.settings_repo import SettingsRepository
from db.constants import AdminRole
from bot.states import (
    AddMovieSG, AddSeriesSG, AddSeasonSG, AddEpisodeSG,
    AddChannelSG, BroadcastSG, AddAdminSG, SettingsSG, AdSG,
)
from bot.keyboards.admin import (
    confirm_kb, skip_kb, broadcast_after_content_kb,
    broadcast_segment_kb, broadcast_confirm_kb, broadcast_controls,
    admin_main_reply_kb, parse_buttons_text,
)
import logging
import asyncio
import json

logger = logging.getLogger(__name__)
router = Router()


# ════════════════════════════════════════════════════════════════════════════
# KINO QO'SHISH FSM  (video → kod → nom → tavsif → tasdiqlash)
# ════════════════════════════════════════════════════════════════════════════

@router.message(AddMovieSG.video)
async def fsm_movie_video(message: Message, state: FSMContext):
    """1) Video yoki fayl qabul qilish."""
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    if not file_id:
        await message.reply("Video yoki fayl yuboring:")
        return
    await state.update_data(file_id=file_id)
    # Auto-kod tavsiya
    await message.reply(
        "Kino kodi — keyingi avtomatik kod tayyor.\n"
        "Avto kod uchun ⏩ O'tkazish bosing yoki o'zingiz kiriting:",
        reply_markup=skip_kb("auto_code")
    )
    await state.set_state(AddMovieSG.code)


@router.callback_query(F.data == "auto_code", AddMovieSG.code)
async def fsm_movie_auto_code(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    """Auto-kod tayinlash."""
    code = "1"
    if session:
        repo = MovieRepository(session)
        code = await repo.get_next_code()
    await state.update_data(code=code)
    await call.message.answer(f"Kod: <code>{code}</code>\n\nKino nomini kiriting:")
    await state.set_state(AddMovieSG.title)
    await call.answer()


@router.message(AddMovieSG.code)
async def fsm_movie_code(message: Message, state: FSMContext, session: AsyncSession | None = None):
    """Qo'lda kod kiritish."""
    code = message.text.strip()
    if session:
        repo = MovieRepository(session)
        existing = await repo.get_by_code(code)
        if existing:
            await message.reply(f"❌ Kod <code>{code}</code> allaqachon mavjud. Boshqa kod kiriting:")
            return
    await state.update_data(code=code)
    await message.reply("Kino nomini kiriting:")
    await state.set_state(AddMovieSG.title)


@router.message(AddMovieSG.title)
async def fsm_movie_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.reply(
        "Kino tavsifini kiriting yoki ⏩ O'tkazish bosing:",
        reply_markup=skip_kb("skip_desc")
    )
    await state.set_state(AddMovieSG.description)


@router.callback_query(F.data == "skip_desc", AddMovieSG.description)
async def fsm_movie_skip_desc(call: CallbackQuery, state: FSMContext):
    await state.update_data(description=None)
    data = await state.get_data()
    text = (
        f"📋 <b>Ko'rik</b>\n\n"
        f"Kod: <code>{data['code']}</code>\n"
        f"Nom: {data['title']}\n"
        f"Tavsif: —"
    )
    await call.message.answer(text, reply_markup=confirm_kb("movie"))
    await state.set_state(AddMovieSG.confirm)
    await call.answer()


@router.message(AddMovieSG.description)
async def fsm_movie_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    data = await state.get_data()
    text = (
        f"📋 <b>Ko'rik</b>\n\n"
        f"Kod: <code>{data['code']}</code>\n"
        f"Nom: {data['title']}\n"
        f"Tavsif: {data.get('description', '—')}"
    )
    await message.answer(text, reply_markup=confirm_kb("movie"))
    await state.set_state(AddMovieSG.confirm)


@router.callback_query(F.data == "movie_confirm", AddMovieSG.confirm)
async def fsm_movie_confirm(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session:
        await call.answer("Sessiya yo'q", show_alert=True)
        return
    data = await state.get_data()
    repo = MovieRepository(session)
    movie = await repo.create(
        code=data["code"],
        title=data["title"],
        video_file_id=data["file_id"],
        description=data.get("description"),
    )
    await session.commit()

    # Baza kanalga yuborish
    try:
        from bot.loader import bot
        from config import settings as app_settings
        base_ch = app_settings.BASE_CHANNEL_ID
        if not base_ch:
            settings_repo = SettingsRepository(session)
            base_ch_str = await settings_repo.get("base_channel_id")
            base_ch = int(base_ch_str) if base_ch_str else None
        if base_ch:
            await bot.send_video(
                base_ch, data["file_id"],
                caption=f"🎬 {movie.title}\nKod: {movie.code}"
            )
    except Exception as e:
        logger.warning(f"Baza kanalga yuborishda xatolik: {e}")

    await call.message.edit_text(
        f"✅ Kino qo'shildi!\n\n"
        f"Kod: <code>{movie.code}</code>\n"
        f"Nom: {movie.title}"
    )
    await state.clear()
    await call.answer("✅ Saqlandi!", show_alert=True)


@router.callback_query(F.data == "movie_cancel", AddMovieSG.confirm)
async def fsm_movie_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Kino qo'shish bekor qilindi.")
    await call.answer()


# ════════════════════════════════════════════════════════════════════════════
# SERIAL QO'SHISH FSM  (nom → kod → tavsif → tasdiqlash)
# ════════════════════════════════════════════════════════════════════════════

@router.message(AddSeriesSG.title)
async def fsm_series_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.reply(
        "Serial kodi — avto uchun ⏩ O'tkazish bosing yoki o'zingiz kiriting:",
        reply_markup=skip_kb("auto_series_code")
    )
    await state.set_state(AddSeriesSG.code)


@router.callback_query(F.data == "auto_series_code", AddSeriesSG.code)
async def fsm_series_auto_code(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    code = "1"
    if session:
        repo = SeriesRepository(session)
        code = await repo.get_next_code()
    await state.update_data(code=code)
    await call.message.answer(
        f"Kod: <code>{code}</code>\n\nSerial tavsifini kiriting yoki ⏩:",
        reply_markup=skip_kb("skip_series_desc")
    )
    await state.set_state(AddSeriesSG.description)
    await call.answer()


@router.message(AddSeriesSG.code)
async def fsm_series_code(message: Message, state: FSMContext, session: AsyncSession | None = None):
    code = message.text.strip()
    if session:
        repo = SeriesRepository(session)
        existing = await repo.get_by_code(code)
        if existing:
            await message.reply(f"❌ Kod <code>{code}</code> mavjud. Boshqa kiriting:")
            return
    await state.update_data(code=code)
    await message.reply(
        "Serial tavsifini kiriting yoki ⏩:",
        reply_markup=skip_kb("skip_series_desc")
    )
    await state.set_state(AddSeriesSG.description)


@router.callback_query(F.data == "skip_series_desc", AddSeriesSG.description)
async def fsm_series_skip_desc(call: CallbackQuery, state: FSMContext):
    await state.update_data(description=None)
    data = await state.get_data()
    text = f"📋 <b>Ko'rik</b>\n\nKod: <code>{data['code']}</code>\nNom: {data['title']}\nTavsif: —"
    await call.message.answer(text, reply_markup=confirm_kb("series"))
    await state.set_state(AddSeriesSG.confirm)
    await call.answer()


@router.message(AddSeriesSG.description)
async def fsm_series_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    data = await state.get_data()
    text = f"📋 <b>Ko'rik</b>\n\nKod: <code>{data['code']}</code>\nNom: {data['title']}\nTavsif: {data['description']}"
    await message.answer(text, reply_markup=confirm_kb("series"))
    await state.set_state(AddSeriesSG.confirm)


@router.callback_query(F.data == "series_confirm", AddSeriesSG.confirm)
async def fsm_series_confirm(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session:
        return await call.answer("Sessiya yo'q", show_alert=True)
    data = await state.get_data()
    repo = SeriesRepository(session)
    s = await repo.create(code=data["code"], title=data["title"], description=data.get("description"))
    await session.commit()
    await call.message.edit_text(f"✅ Serial qo'shildi!\nKod: <code>{s.code}</code>\nNom: {s.title}")
    await state.clear()
    await call.answer("✅ Saqlandi!", show_alert=True)


@router.callback_query(F.data == "series_cancel", AddSeriesSG.confirm)
async def fsm_series_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Bekor qilindi.")
    await call.answer()


# ════════════════════════════════════════════════════════════════════════════
# SEZON QO'SHISH  (serial tanlash → sezon raqami → tasdiqlash)
# ════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("season_add:"))
async def fsm_season_start(call: CallbackQuery, state: FSMContext):
    series_id = int(call.data.split(":")[1])
    await state.update_data(series_id=series_id)
    await call.message.answer("Sezon raqamini kiriting:")
    await state.set_state(AddSeasonSG.season_number)
    await call.answer()


@router.message(AddSeasonSG.season_number)
async def fsm_season_number(message: Message, state: FSMContext, session: AsyncSession | None = None):
    try:
        num = int(message.text.strip())
    except ValueError:
        await message.reply("Raqam kiriting:")
        return
    if not session:
        return
    data = await state.get_data()
    repo = SeriesRepository(session)
    season = await repo.add_season(data["series_id"], num)
    await session.commit()
    await message.reply(f"✅ Sezon {num} qo'shildi!")
    await state.clear()


# ════════════════════════════════════════════════════════════════════════════
# EPIZOD QO'SHISH  (serial → sezon → ep raqami → nom → video → tasdiqlash)
# ════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("episode_add:"))
async def fsm_episode_start(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    series_id = int(call.data.split(":")[1])
    await state.update_data(series_id=series_id)
    if not session:
        return await call.answer()
    repo = SeriesRepository(session)
    seasons = await repo.get_seasons(series_id)
    if not seasons:
        await call.answer("Avval sezon qo'shing!", show_alert=True)
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for sn in seasons:
        builder.row(InlineKeyboardButton(
            text=f"Sezon {sn.season_number}",
            callback_data=f"ep_season:{sn.id}"
        ))
    await call.message.answer("Sezonni tanlang:", reply_markup=builder.as_markup())
    await state.set_state(AddEpisodeSG.select_season)
    await call.answer()


@router.callback_query(F.data.startswith("ep_season:"), AddEpisodeSG.select_season)
async def fsm_episode_season(call: CallbackQuery, state: FSMContext):
    season_id = int(call.data.split(":")[1])
    await state.update_data(season_id=season_id)
    await call.message.answer("Epizod raqamini kiriting:")
    await state.set_state(AddEpisodeSG.episode_number)
    await call.answer()


@router.message(AddEpisodeSG.episode_number)
async def fsm_episode_number(message: Message, state: FSMContext):
    try:
        num = int(message.text.strip())
    except ValueError:
        await message.reply("Raqam kiriting:")
        return
    await state.update_data(episode_number=num)
    await message.reply(
        "Epizod nomini kiriting yoki ⏩:",
        reply_markup=skip_kb("skip_ep_title")
    )
    await state.set_state(AddEpisodeSG.title)


@router.callback_query(F.data == "skip_ep_title", AddEpisodeSG.title)
async def fsm_episode_skip_title(call: CallbackQuery, state: FSMContext):
    await state.update_data(ep_title=None)
    await call.message.answer("Epizod videosini yuboring:")
    await state.set_state(AddEpisodeSG.video)
    await call.answer()


@router.message(AddEpisodeSG.title)
async def fsm_episode_title(message: Message, state: FSMContext):
    await state.update_data(ep_title=message.text.strip())
    await message.reply("Epizod videosini yuboring:")
    await state.set_state(AddEpisodeSG.video)


@router.message(AddEpisodeSG.video)
async def fsm_episode_video(message: Message, state: FSMContext, session: AsyncSession | None = None):
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    if not file_id:
        await message.reply("Video yoki fayl yuboring:")
        return
    if not session:
        return
    data = await state.get_data()
    repo = SeriesRepository(session)
    ep = await repo.add_episode(
        season_id=data["season_id"],
        episode_number=data["episode_number"],
        video_file_id=file_id,
        title=data.get("ep_title"),
    )
    await session.commit()

    # Baza kanalga yuborish
    try:
        from bot.loader import bot
        from config import settings as app_settings
        base_ch = app_settings.BASE_CHANNEL_ID
        if not base_ch:
            settings_repo = SettingsRepository(session)
            base_ch_str = await settings_repo.get("base_channel_id")
            base_ch = int(base_ch_str) if base_ch_str else None
        if base_ch:
            await bot.send_video(
                base_ch, file_id,
                caption=f"📺 Epizod {ep.episode_number}\n{data.get('ep_title', '')}"
            )
    except Exception as e:
        logger.warning(f"Baza kanal xatolik: {e}")

    await message.reply(f"✅ Epizod {ep.episode_number} qo'shildi!")
    await state.clear()


# ════════════════════════════════════════════════════════════════════════════
# KANAL QO'SHISH FSM  (chat_id → auto-detect → majburiy? → saqlash)
# ════════════════════════════════════════════════════════════════════════════

@router.message(AddChannelSG.chat_id)
async def fsm_channel_id(message: Message, state: FSMContext, session: AsyncSession | None = None):
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.reply("Chat ID raqam bo'lishi kerak:")
        return

    # Auto-detect via Telegram API
    title = f"Kanal {chat_id}"
    ch_type = "public"
    members = 0
    invite_link = None
    try:
        from bot.loader import bot
        chat = await bot.get_chat(chat_id)
        title = chat.title or title
        if chat.type in ("supergroup", "group"):
            ch_type = "public"
        else:
            ch_type = "public" if chat.username else "private"
        try:
            members = await bot.get_chat_member_count(chat_id)
        except Exception:
            pass
        invite_link = chat.invite_link
    except Exception as e:
        logger.warning(f"get_chat xatolik: {e}")
        await message.reply(
            f"⚠️ Kanal ma'lumotlarini olishda xatolik: {str(e)[:100]}\n"
            "Bot kanalda admin ekanligini tekshiring.\n"
            "Davom etamizmi?",
            reply_markup=confirm_kb("ch_force")
        )
        await state.update_data(tg_chat_id=chat_id, title=title, ch_type=ch_type, members=members, invite_link=invite_link)
        await state.set_state(AddChannelSG.is_required)
        return

    await state.update_data(tg_chat_id=chat_id, title=title, ch_type=ch_type, members=members, invite_link=invite_link)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha — majburiy", callback_data="ch_req:yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="ch_req:no"),
        ]
    ])
    await message.reply(
        f"📋 Kanal topildi:\n"
        f"Nomi: <b>{title}</b>\n"
        f"Turi: {ch_type}\n"
        f"A'zolar: {members}\n\n"
        f"Majburiy obuna?",
        reply_markup=kb
    )
    await state.set_state(AddChannelSG.is_required)


@router.callback_query(F.data.startswith("ch_req:"), AddChannelSG.is_required)
async def fsm_channel_required(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    is_req = call.data.split(":")[1] == "yes"
    data = await state.get_data()
    if not session:
        return await call.answer("Sessiya yo'q", show_alert=True)
    repo = ChannelRepository(session)
    existing = await repo.get_by_tg_chat_id(data["tg_chat_id"])
    if existing:
        await call.message.answer(f"Bu kanal allaqachon mavjud: {existing.title}")
        await state.clear()
        return await call.answer()
    ch = await repo.create(
        tg_chat_id=data["tg_chat_id"],
        title=data["title"],
        channel_type=data["ch_type"],
        invite_link=data.get("invite_link"),
        is_required=is_req,
    )
    if data.get("members"):
        await repo.update_members_count(ch.id, data["members"])
    await session.commit()
    req = "Ha ✅" if is_req else "Yo'q ❌"
    await call.message.edit_text(
        f"✅ Kanal qo'shildi!\n\n"
        f"Nomi: {ch.title}\nID: {ch.tg_chat_id}\n"
        f"Turi: {ch.type}\nMajburiy: {req}\n"
        f"A'zolar: {data.get('members', 0)}"
    )
    await state.clear()
    await call.answer("✅ Saqlandi!", show_alert=True)


@router.callback_query(F.data == "ch_force_confirm", AddChannelSG.is_required)
async def fsm_channel_force_confirm(call: CallbackQuery, state: FSMContext):
    """Force add despite error — ask required."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha — majburiy", callback_data="ch_req:yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="ch_req:no"),
        ]
    ])
    await call.message.answer("Majburiy obuna?", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "ch_force_cancel", AddChannelSG.is_required)
async def fsm_channel_force_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Bekor qilindi.")
    await call.answer()


# ════════════════════════════════════════════════════════════════════════════
# BROADCAST FSM  (rejim → content → tugmalar → segment → ko'rik → yuborish)
# ════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("bc_mode:"), BroadcastSG.mode)
async def fsm_bc_mode(call: CallbackQuery, state: FSMContext):
    mode = call.data.split(":")[1]
    await state.update_data(mode=mode)
    if mode == "custom":
        await call.message.answer("📝 Xabar matnini yoki media (rasm/video/fayl) yuboring:")
    elif mode == "forward":
        await call.message.answer("↗️ Forward qilmoqchi bo'lgan xabarni shu chatga forward qiling:")
    else:
        await call.message.answer("📋 Copy qilmoqchi bo'lgan xabarni shu chatga yuboring:")
    await state.set_state(BroadcastSG.content)
    await call.answer()


@router.callback_query(F.data == "bc_cancel")
async def fsm_bc_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Broadcast bekor qilindi.")
    await call.answer()


@router.message(BroadcastSG.content)
async def fsm_bc_content(message: Message, state: FSMContext):
    """Xabar mazmunini qabul qilish."""
    data = await state.get_data()
    mode = data.get("mode", "custom")

    if mode == "forward" and message.forward_date:
        await state.update_data(
            forward_from_chat_id=message.forward_from_chat.id if message.forward_from_chat else message.chat.id,
            forward_message_id=message.message_id,
        )
        await message.reply(
            "✅ Forward xabar qabul qilindi.",
            reply_markup=broadcast_after_content_kb()
        )
        await state.set_state(BroadcastSG.buttons)
        return

    # Custom yoki copy
    text = message.text or message.caption or ""
    media = {}
    if message.photo:
        media["media_photo"] = message.photo[-1].file_id
    elif message.video:
        media["media_video"] = message.video.file_id
    elif message.document:
        media["media_document"] = message.document.file_id
    elif message.animation:
        media["media_animation"] = message.animation.file_id
    elif message.audio:
        media["media_audio"] = message.audio.file_id
    elif message.sticker:
        media["media_sticker"] = message.sticker.file_id

    await state.update_data(text=text, **media)
    await message.reply(
        "✅ Xabar qabul qilindi.\nNima qilasiz?",
        reply_markup=broadcast_after_content_kb()
    )
    await state.set_state(BroadcastSG.buttons)


@router.callback_query(F.data == "bc_add_buttons", BroadcastSG.buttons)
async def fsm_bc_add_buttons(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
        "Tugmalarni quyidagi formatda yozing:\n\n"
        "<code>Tugma matni | https://link.com</code>\n"
        "<code>Tugma 2 | https://link2.com</code>\n\n"
        "Har bir qator — alohida tugma."
    )
    await call.answer()


@router.message(BroadcastSG.buttons)
async def fsm_bc_buttons_text(message: Message, state: FSMContext):
    """Tugmalar matnini qabul qilish."""
    kb = parse_buttons_text(message.text)
    if kb:
        # Serialize buttons to JSON for storage
        buttons_data = []
        for row in kb.inline_keyboard:
            for btn in row:
                buttons_data.append({
                    "text": btn.text,
                    "url": btn.url,
                    "callback_data": btn.callback_data,
                })
        await state.update_data(buttons=buttons_data)
        await message.reply("✅ Tugmalar qo'shildi.", reply_markup=broadcast_after_content_kb())
    else:
        await message.reply("❌ Formatni tekshiring. Har qator: Matn | link")


@router.callback_query(F.data == "bc_segment", BroadcastSG.buttons)
async def fsm_bc_segment(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup(reply_markup=broadcast_segment_kb())
    await state.set_state(BroadcastSG.segment)
    await call.answer()


@router.callback_query(F.data.startswith("bc_seg:"), BroadcastSG.segment)
async def fsm_bc_segment_select(call: CallbackQuery, state: FSMContext):
    seg = call.data.split(":")[1]
    await state.update_data(segment=seg)
    await call.answer(f"Segment: {seg}", show_alert=True)
    await state.set_state(BroadcastSG.buttons)
    await call.message.edit_reply_markup(reply_markup=broadcast_after_content_kb())


@router.callback_query(F.data == "bc_back_content", BroadcastSG.segment)
async def fsm_bc_back_content(call: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastSG.buttons)
    await call.message.edit_reply_markup(reply_markup=broadcast_after_content_kb())
    await call.answer()


@router.callback_query(F.data == "bc_preview", BroadcastSG.buttons)
async def fsm_bc_preview(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    data = await state.get_data()
    text = data.get("text", "")
    seg = data.get("segment", "all")

    target = "?"
    if session:
        user_repo = UserRepository(session)
        target = await user_repo.get_total_count()

    preview = (
        f"📢 <b>Broadcast ko'rik</b>\n\n"
        f"{text}\n\n"
        f"Rejim: {data.get('mode', 'custom')}\n"
        f"Segment: {seg}\n"
        f"👥 Maqsad: ~{target} foydalanuvchi"
    )
    media_keys = [k for k in data if k.startswith("media_")]
    if media_keys:
        preview += f"\n📎 Media: {', '.join(k.replace('media_', '') for k in media_keys)}"
    if data.get("buttons"):
        preview += f"\n🔘 Tugmalar: {len(data['buttons'])} ta"

    await call.message.answer(preview, reply_markup=broadcast_confirm_kb())
    await state.set_state(BroadcastSG.preview)
    await call.answer()


@router.callback_query(F.data == "bc_confirm", BroadcastSG.preview)
async def fsm_bc_confirm(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session:
        return await call.answer("Sessiya yo'q", show_alert=True)

    data = await state.get_data()
    bc_repo = BroadcastRepository(session)
    bc = await bc_repo.create(admin_id=call.from_user.id, mode=data.get("mode", "custom"))
    bc.text = data.get("text")
    bc.media_photo = data.get("media_photo")
    bc.media_video = data.get("media_video")
    bc.media_document = data.get("media_document")
    bc.media_animation = data.get("media_animation")
    bc.segment = {"type": data.get("segment", "all")}
    if data.get("buttons"):
        bc.buttons = data["buttons"]
    await session.commit()

    await call.message.edit_text(
        f"🚀 Broadcast #{bc.id} ishga tushirildi...",
        reply_markup=broadcast_controls(bc.id)
    )
    await call.answer()
    await state.clear()

    # Background broadcast
    from services.broadcaster import BroadcastEngine
    from bot.loader import bot
    engine = BroadcastEngine(session, bot)
    asyncio.create_task(engine.start(bc.id, call.from_user.id))


# ════════════════════════════════════════════════════════════════════════════
# ADMIN QO'SHISH FSM
# ════════════════════════════════════════════════════════════════════════════

@router.message(AddAdminSG.user_input, F.text)
async def fsm_admin_input(message: Message, state: FSMContext, session: AsyncSession | None = None):
    if not session:
        await state.clear()
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.reply("Format: <code>USER_ID rol</code>")
        return
    try:
        user_id = int(parts[0])
        role = parts[1].lower()
    except ValueError:
        await message.reply("User ID raqam bo'lishi kerak")
        return
    valid_roles = [r.value for r in AdminRole]
    if role not in valid_roles:
        await message.reply(f"Noto'g'ri rol. Mavjud: {', '.join(valid_roles)}")
        return
    admin_repo = AdminRepository(session)
    user_repo = UserRepository(session)
    await user_repo.get_or_create(user_id=user_id, first_name="Admin")
    existing = await admin_repo.get_by_user_id(user_id)
    if existing:
        await admin_repo.update_role(user_id, role)
        await session.commit()
        await message.reply(f"✅ Admin {user_id} roli <code>{role}</code> ga yangilandi")
    else:
        await admin_repo.create(user_id, role=role)
        await session.commit()
        await message.reply(f"✅ Yangi admin: {user_id} ({role})")
    await state.clear()


# ════════════════════════════════════════════════════════════════════════════
# SOZLAMALAR FSM
# ════════════════════════════════════════════════════════════════════════════

@router.message(SettingsSG.broadcast_rate)
async def fsm_set_bc_rate(message: Message, state: FSMContext, session: AsyncSession | None = None):
    try:
        rate = int(message.text.strip())
        if not 1 <= rate <= 30:
            raise ValueError
    except ValueError:
        await message.reply("1 dan 30 gacha raqam kiriting:")
        return
    if session:
        repo = SettingsRepository(session)
        await repo.set("broadcast_bot_rate", str(rate))
        await session.commit()
    await message.reply(f"✅ Broadcast tezligi: {rate} msg/sec", reply_markup=admin_main_reply_kb())
    await state.clear()


@router.message(SettingsSG.base_channel)
async def fsm_set_base_channel(message: Message, state: FSMContext, session: AsyncSession | None = None):
    try:
        ch_id = int(message.text.strip())
    except ValueError:
        await message.reply("Raqam kiriting:")
        return
    if session:
        repo = SettingsRepository(session)
        await repo.set("base_channel_id", str(ch_id))
        await session.commit()
    await message.reply(f"✅ Baza kanal: {ch_id}", reply_markup=admin_main_reply_kb())
    await state.clear()


@router.message(SettingsSG.restore_file, F.document)
async def fsm_set_restore(message: Message, state: FSMContext, session: AsyncSession | None = None):
    if not session:
        await state.clear()
        return
    try:
        from bot.loader import bot
        import tempfile
        file = await bot.get_file(message.document.file_id)
        tmp = tempfile.NamedTemporaryFile(suffix=".json.gz", delete=False)
        await bot.download_file(file.file_path, tmp.name)
        from services.backup import BackupService
        svc = BackupService(session)
        ok = await svc.restore(tmp.name)
        if ok:
            await message.reply("✅ Backup tiklandi!", reply_markup=admin_main_reply_kb())
        else:
            await message.reply("❌ Tiklashda xatolik")
    except Exception as e:
        logger.error(f"Restore error: {e}")
        await message.reply(f"❌ Xatolik: {str(e)[:100]}")
    await state.clear()


# ════════════════════════════════════════════════════════════════════════════
# REKLAMA YARATISH FSM
# ════════════════════════════════════════════════════════════════════════════

@router.message(AdSG.content)
async def fsm_ad_content(message: Message, state: FSMContext):
    """Reklama mazmunini qabul qilish."""
    text = message.text or message.caption or ""
    media = {}
    media_type = None
    if message.photo:
        media["media_file_id"] = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media["media_file_id"] = message.video.file_id
        media_type = "video"
    elif message.animation:
        media["media_file_id"] = message.animation.file_id
        media_type = "animation"
    elif message.document:
        media["media_file_id"] = message.document.file_id
        media_type = "document"

    await state.update_data(ad_text=text, media_type=media_type, **media)
    await message.reply(
        "Reklama muddatini kiriting (kunlarda, masalan: 7).\n"
        "⏩ O'tkazish — cheksiz:",
        reply_markup=skip_kb("skip_ad_duration")
    )
    await state.set_state(AdSG.duration)


@router.callback_query(F.data == "skip_ad_duration", AdSG.duration)
async def fsm_ad_skip_duration(call: CallbackQuery, state: FSMContext):
    await state.update_data(duration_days=None)
    data = await state.get_data()
    text = (
        f"📣 <b>Reklama ko'rik</b>\n\n"
        f"{data.get('ad_text', '')}\n\n"
        f"Media: {data.get('media_type', '—')}\n"
        f"Muddat: cheksiz"
    )
    await call.message.answer(text, reply_markup=confirm_kb("ad"))
    await state.set_state(AdSG.confirm)
    await call.answer()


@router.message(AdSG.duration)
async def fsm_ad_duration(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days < 1:
            raise ValueError
    except ValueError:
        await message.reply("Musbat raqam kiriting yoki ⏩ O'tkazish bosing:")
        return
    await state.update_data(duration_days=days)
    data = await state.get_data()
    text = (
        f"📣 <b>Reklama ko'rik</b>\n\n"
        f"{data.get('ad_text', '')}\n\n"
        f"Media: {data.get('media_type', '—')}\n"
        f"Muddat: {days} kun"
    )
    await message.answer(text, reply_markup=confirm_kb("ad"))
    await state.set_state(AdSG.confirm)


@router.callback_query(F.data == "ad_confirm", AdSG.confirm)
async def fsm_ad_confirm(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session:
        return await call.answer("Sessiya yo'q", show_alert=True)
    data = await state.get_data()
    from db.repositories.ad_repo import AdRepository
    from datetime import datetime, timedelta
    repo = AdRepository(session)
    expires = None
    if data.get("duration_days"):
        expires = datetime.utcnow() + timedelta(days=data["duration_days"])
    ad = await repo.create(
        admin_id=call.from_user.id,
        text=data.get("ad_text"),
        media_file_id=data.get("media_file_id"),
        media_type=data.get("media_type"),
        expires_at=expires,
    )
    await session.commit()
    await call.message.edit_text(f"✅ Reklama #{ad.id} yaratildi!")
    await state.clear()
    await call.answer("✅ Saqlandi!", show_alert=True)


@router.callback_query(F.data == "ad_cancel", AdSG.confirm)
async def fsm_ad_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Reklama bekor qilindi.")
    await call.answer()
