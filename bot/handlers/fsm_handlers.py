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
    AddChannelSG, BroadcastSG, AddAdminSG, SettingsSG,
    EditMovieSG, EditSeriesSG, SearchMovieSG,
)
from bot.keyboards.admin import (
    confirm_kb, skip_kb, broadcast_after_content_kb,
    broadcast_segment_kb, broadcast_custom_segment_kb,
    broadcast_confirm_kb, broadcast_controls,
    channel_type_kb, channel_required_kb,
    movie_list_kb, movie_detail_kb, series_list_kb,
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
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    if not file_id:
        await message.reply("Video yoki fayl yuboring:")
        return
    await state.update_data(file_id=file_id)
    await message.reply(
        "Kino kodi — keyingi avtomatik kod tayyor.\n"
        "Avto kod uchun ⏩ O'tkazish bosing yoki o'zingiz kiriting:",
        reply_markup=skip_kb("auto_code")
    )
    await state.set_state(AddMovieSG.code)


@router.callback_query(F.data == "auto_code", AddMovieSG.code)
async def fsm_movie_auto_code(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
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
# KINO TAHRIRLASH FSM
# ════════════════════════════════════════════════════════════════════════════

@router.message(EditMovieSG.value)
async def fsm_movie_edit_value(message: Message, state: FSMContext, session: AsyncSession | None = None):
    if not session:
        await state.clear()
        return
    data = await state.get_data()
    movie_id, field = data.get("movie_id"), data.get("field")
    repo = MovieRepository(session)

    update_value = None
    if field == "video":
        if message.video:
            update_value = message.video.file_id
        elif message.document:
            update_value = message.document.file_id
        else:
            await message.reply("Video yoki fayl yuboring:")
            return
    elif field == "year":
        try:
            update_value = int(message.text.strip())
        except (ValueError, AttributeError):
            await message.reply("Yil — raqam (masalan: 2024):")
            return
    elif field == "genres":
        update_value = [g.strip() for g in (message.text or "").split(",") if g.strip()]
    elif field == "code":
        new_code = (message.text or "").strip()
        existing = await repo.get_by_code(new_code)
        if existing and existing.id != movie_id:
            await message.reply(f"❌ Kod <code>{new_code}</code> band. Boshqa kod kiriting:")
            return
        update_value = new_code
    else:  # title, description
        update_value = (message.text or "").strip()

    await repo.update(movie_id, **{field: update_value})
    await session.commit()
    await message.reply(f"✅ <b>{field}</b> yangilandi.")
    await state.clear()


# ════════════════════════════════════════════════════════════════════════════
# KINO QIDIRUV (admin)
# ════════════════════════════════════════════════════════════════════════════

@router.message(SearchMovieSG.query)
async def fsm_movie_search(message: Message, state: FSMContext, session: AsyncSession | None = None):
    if not session:
        await state.clear()
        return
    query = (message.text or "").strip()
    repo = MovieRepository(session)
    movies = await repo.search(query, limit=20)
    if not movies:
        await message.reply("Hech narsa topilmadi.")
        await state.clear()
        return
    # Use a custom inline keyboard with results
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for m in movies:
        builder.row(InlineKeyboardButton(
            text=f"🎬 {m.code} — {m.title}",
            callback_data=f"movie_view:{m.id}"
        ))
    await message.reply(f"🔍 <b>Natijalar:</b> {len(movies)} ta", reply_markup=builder.as_markup())
    await state.clear()


# ════════════════════════════════════════════════════════════════════════════
# SERIAL QO'SHISH FSM
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
# SERIAL TAHRIRLASH FSM
# ════════════════════════════════════════════════════════════════════════════

@router.message(EditSeriesSG.value)
async def fsm_series_edit_value(message: Message, state: FSMContext, session: AsyncSession | None = None):
    if not session:
        await state.clear()
        return
    data = await state.get_data()
    series_id, field = data.get("series_id"), data.get("field")
    repo = SeriesRepository(session)

    update_value = None
    if field == "year":
        try:
            update_value = int(message.text.strip())
        except (ValueError, AttributeError):
            await message.reply("Yil — raqam:")
            return
    elif field == "genres":
        update_value = [g.strip() for g in (message.text or "").split(",") if g.strip()]
    elif field == "code":
        new_code = (message.text or "").strip()
        existing = await repo.get_by_code(new_code)
        if existing and existing.id != series_id:
            await message.reply(f"❌ Kod <code>{new_code}</code> band:")
            return
        update_value = new_code
    else:
        update_value = (message.text or "").strip()

    await repo.update(series_id, **{field: update_value})
    await session.commit()
    await message.reply(f"✅ <b>{field}</b> yangilandi.")
    await state.clear()


# ════════════════════════════════════════════════════════════════════════════
# SEZON QO'SHISH
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
# EPIZOD QO'SHISH
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
# KANAL QO'SHISH FSM — Yangi 5-qadamli wizard (3 turi)
# ════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("ch_type:"), AddChannelSG.channel_type)
async def fsm_channel_type(call: CallbackQuery, state: FSMContext):
    """1) Tur tanlash → 2) chat_id so'rash."""
    ch_type = call.data.split(":")[1]
    await state.update_data(ch_type=ch_type)
    type_label = {
        "public": "📢 Oddiy (public)",
        "private": "🔒 Yopiq (invite link)",
        "request_join": "✋ So'rovli kanal/guruh"
    }.get(ch_type, ch_type)
    await call.message.edit_text(
        f"<b>Tur:</b> {type_label}\n\n"
        f"Endi kanal/guruh chat ID sini yuboring\n"
        f"(masalan: <code>-1001234567890</code>)\n\n"
        f"⚠️ Bot kanalda admin bo'lishi shart!"
    )
    await state.set_state(AddChannelSG.chat_id)
    await call.answer()


@router.message(AddChannelSG.chat_id)
async def fsm_channel_id(message: Message, state: FSMContext, session: AsyncSession | None = None):
    """2) Chat ID qabul qilish va auto-detect."""
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.reply("Chat ID raqam bo'lishi kerak (masalan: -1001234567890):")
        return

    data = await state.get_data()
    ch_type = data.get("ch_type", "public")

    title = f"Kanal {chat_id}"
    members = 0
    detected_username = None
    detected_invite = None
    try:
        from bot.loader import bot
        chat = await bot.get_chat(chat_id)
        title = chat.title or title
        detected_username = chat.username
        detected_invite = chat.invite_link  # admin tomonidan oldin yaratilgan invite (agar bor bo'lsa)
        try:
            members = await bot.get_chat_member_count(chat_id)
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"get_chat: {e}")
        await message.reply(
            f"⚠️ Kanal ma'lumotlarini olishda xatolik: {str(e)[:100]}\n"
            "Bot kanalda admin ekanligini tekshiring va qayta yuboring:"
        )
        return

    await state.update_data(
        tg_chat_id=chat_id, title=title, members=members,
        detected_username=detected_username, detected_invite=detected_invite,
    )

    # 3) Invite link (ch_type ga qarab)
    if ch_type == "public" and detected_username:
        # Public username mavjud — auto link, invite link kiritish kerak emas
        await state.update_data(invite_link=f"https://t.me/{detected_username}")
        await _ask_required(message, state)
    else:
        # Private yoki request_join — admin invite link kiritadi
        if ch_type == "request_join":
            prompt = (
                f"📋 <b>{title}</b> topildi (a'zo: {members})\n\n"
                f"✋ <b>So'rovli (Join Request)</b> link yuboring:\n"
                f"Masalan: <code>https://t.me/+ABCxyz123</code>\n\n"
                f"⚠️ Admin tomonidan yaratilgan, \"Approve required\" yoqilgan link bo'lishi shart.\n"
                f"Bot kanalda admin bo'lishi va so'rovlarni qabul qilishi kerak."
            )
        else:  # private
            prompt = (
                f"📋 <b>{title}</b> topildi (a'zo: {members})\n\n"
                f"🔒 <b>Yopiq kanal</b> uchun invite link yuboring:\n"
                f"Masalan: <code>https://t.me/+ABCxyz123</code>\n\n"
                f"Yoki saqlangan link uchun ⏩:",
            )
            prompt = prompt[0] if isinstance(prompt, tuple) else prompt
        await message.reply(prompt, reply_markup=skip_kb("ch_skip_link"))
        await state.set_state(AddChannelSG.invite_link_input)


@router.callback_query(F.data == "ch_skip_link", AddChannelSG.invite_link_input)
async def fsm_channel_skip_link(call: CallbackQuery, state: FSMContext):
    """Invite link kiritmaslik — saqlangan/aniqlangan invite ishlatiladi (faqat private uchun)."""
    data = await state.get_data()
    ch_type = data.get("ch_type", "private")
    if ch_type == "request_join":
        await call.answer("So'rovli kanal uchun link MAJBURIY", show_alert=True)
        return
    await state.update_data(invite_link=data.get("detected_invite"))
    await _ask_required(call.message, state)
    await call.answer()


@router.message(AddChannelSG.invite_link_input)
async def fsm_channel_invite_link(message: Message, state: FSMContext):
    """3) Admin invite link yuboradi."""
    link = (message.text or "").strip()
    if not (link.startswith("https://t.me/") or link.startswith("http://t.me/") or link.startswith("tg://")):
        await message.reply("❌ To'g'ri link yuboring (https://t.me/+...):")
        return
    await state.update_data(invite_link=link)
    await _ask_required(message, state)


async def _ask_required(message: Message, state: FSMContext):
    """4) Majburiy obunani so'rash."""
    data = await state.get_data()
    type_label = {
        "public": "📢 Oddiy",
        "private": "🔒 Yopiq",
        "request_join": "✋ So'rovli"
    }.get(data.get("ch_type"), "📋")
    text = (
        f"<b>Tur:</b> {type_label}\n"
        f"<b>Nomi:</b> {data.get('title')}\n"
        f"<b>ID:</b> <code>{data.get('tg_chat_id')}</code>\n"
        f"<b>Link:</b> {data.get('invite_link') or '—'}\n\n"
        f"Majburiy obuna qilamizmi?"
    )
    await message.answer(text, reply_markup=channel_required_kb())
    await state.set_state(AddChannelSG.is_required)


@router.callback_query(F.data.startswith("ch_req:"), AddChannelSG.is_required)
async def fsm_channel_required(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    """5) Majburiy → saqlash."""
    is_req = call.data.split(":")[1] == "yes"
    data = await state.get_data()
    if not session:
        return await call.answer("Sessiya yo'q", show_alert=True)
    repo = ChannelRepository(session)
    existing = await repo.get_by_tg_chat_id(data["tg_chat_id"])
    if existing:
        await call.message.edit_text(f"❌ Bu kanal allaqachon mavjud: <b>{existing.title}</b>")
        await state.clear()
        return await call.answer()

    ch = await repo.create(
        tg_chat_id=data["tg_chat_id"],
        title=data["title"],
        channel_type=data.get("ch_type", "public"),
        invite_link=data.get("invite_link"),
        is_required=is_req,
    )
    if data.get("members"):
        await repo.update_members_count(ch.id, data["members"])
    await session.commit()

    type_label = {
        "public": "📢 Oddiy",
        "private": "🔒 Yopiq",
        "request_join": "✋ So'rovli"
    }.get(data.get("ch_type"), "📋")
    req = "Ha ✅" if is_req else "Yo'q ❌"
    await call.message.edit_text(
        f"✅ <b>Kanal qo'shildi!</b>\n\n"
        f"Tur: {type_label}\n"
        f"Nomi: {ch.title}\n"
        f"ID: <code>{ch.tg_chat_id}</code>\n"
        f"Link: {ch.invite_link or '—'}\n"
        f"Majburiy: {req}\n"
        f"A'zolar: {data.get('members', 0)}"
    )
    await state.clear()
    await call.answer("✅ Saqlandi!", show_alert=True)


# ════════════════════════════════════════════════════════════════════════════
# BROADCAST FSM — Maximum API
# ════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("bc_mode:"), BroadcastSG.mode)
async def fsm_bc_mode(call: CallbackQuery, state: FSMContext):
    mode = call.data.split(":")[1]
    await state.update_data(mode=mode)
    if mode == "custom":
        await call.message.answer("📝 Xabar matnini yoki media (rasm/video/fayl) yuboring:")
    elif mode == "rich":
        await call.message.answer(
            "🎨 <b>Rich rejim</b>\n\n"
            "Avval xabar matnini yoki media yuboring (matn HTML formatda).\n"
            "So'ngra tugmalar qo'shasiz."
        )
    elif mode == "forward":
        await call.message.answer("↗️ Forward qilmoqchi bo'lgan xabarni shu chatga forward qiling:")
    else:
        await call.message.answer("📋 Copy qilmoqchi bo'lgan xabarni shu chatga yuboring:")
    await state.set_state(BroadcastSG.content)
    await call.answer()


@router.callback_query(F.data == "bc_cancel")
async def fsm_bc_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.edit_text("❌ Broadcast bekor qilindi.")
    except Exception:
        await call.message.answer("❌ Broadcast bekor qilindi.")
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
        "<b>Tugma format:</b>\n\n"
        "<code>Tugma 1 | https://link1.com\n"
        "Tugma 2 | https://link2.com</code>\n\n"
        "<b>1 qatorda 2 tugma:</b>\n"
        "<code>A | url1 :: B | url2</code>\n\n"
        "<b>Yangi qator:</b>\n"
        "<code>A | url1\n"
        "---\n"
        "B | url2</code>\n\n"
        "Callback uchun: <code>Matn | callback:my_data</code>"
    )
    await call.answer()


@router.message(BroadcastSG.buttons)
async def fsm_bc_buttons_text(message: Message, state: FSMContext):
    """Tugmalar matnini qabul qilish."""
    kb = parse_buttons_text(message.text or "")
    if kb:
        buttons_data = []
        for row in kb.inline_keyboard:
            row_data = []
            for btn in row:
                row_data.append({
                    "text": btn.text,
                    "url": btn.url,
                    "callback_data": btn.callback_data,
                })
            buttons_data.append(row_data)
        await state.update_data(buttons=buttons_data)
        await message.reply(
            f"✅ Tugmalar qo'shildi: {sum(len(r) for r in buttons_data)} ta",
            reply_markup=broadcast_after_content_kb()
        )
    else:
        await message.reply("❌ Formatni tekshiring. Har qator: <code>Matn | link</code>")


@router.callback_query(F.data == "bc_segment", BroadcastSG.buttons)
async def fsm_bc_segment(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    target = await _calc_target(session, {"type": "all"}) if session else 0
    await call.message.edit_reply_markup(reply_markup=broadcast_segment_kb(target_count=target))
    await state.set_state(BroadcastSG.segment)
    await call.answer()


@router.callback_query(F.data.startswith("bc_seg:"), BroadcastSG.segment)
async def fsm_bc_segment_select(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    seg = call.data.split(":")[1]
    if seg == "custom":
        await state.update_data(custom_filters={})
        target = await _calc_target(session, _custom_to_segment({})) if session else 0
        await call.message.edit_reply_markup(
            reply_markup=broadcast_custom_segment_kb({}, target_count=target)
        )
        await state.set_state(BroadcastSG.segment_custom)
        await call.answer("Custom filter")
        return
    seg_data = _seg_simple_to_segment(seg)
    target = await _calc_target(session, seg_data) if session else 0
    await state.update_data(segment=seg_data)
    await call.answer(f"Maqsad: {target}", show_alert=True)
    await state.set_state(BroadcastSG.buttons)
    await call.message.edit_reply_markup(reply_markup=broadcast_after_content_kb())


def _seg_simple_to_segment(seg: str) -> dict:
    """Asosiy segment buttondan dict yasash."""
    if seg == "all":
        return {"type": "all"}
    if seg == "premium":
        return {"type": "premium"}
    if seg.startswith("active_"):
        return {"type": "active", "days": int(seg.split("_")[1])}
    if seg.startswith("new_"):
        return {"type": "new", "days": int(seg.split("_")[1])}
    return {"type": "all"}


def _custom_to_segment(filters: dict) -> dict:
    """Custom filter dict ni segment dict ga aylantirish."""
    seg = {"type": "custom"}
    if filters.get("active") and filters["active"] != "all":
        seg["active_days"] = int(filters["active"])
    if filters.get("new") and filters["new"] != "all":
        seg["new_days"] = int(filters["new"])
    if filters.get("lang") and filters["lang"] != "all":
        seg["lang"] = filters["lang"]
    if filters.get("premium") and filters["premium"] != "all":
        seg["premium_only"] = filters["premium"] == "yes"
        seg["non_premium"] = filters["premium"] == "no"
    return seg


async def _calc_target(session, segment: dict) -> int:
    """Maqsad foydalanuvchilar sonini hisoblash."""
    if not session:
        return 0
    try:
        repo = UserRepository(session)
        if hasattr(repo, "count_for_broadcast"):
            return await repo.count_for_broadcast(segment)
        users = await repo.get_users_for_broadcast(segment=segment, limit=100000)
        return len(users)
    except Exception as e:
        logger.warning(f"calc target: {e}")
        return 0


@router.callback_query(F.data.startswith("bc_cf:"), BroadcastSG.segment_custom)
async def fsm_bc_custom_filter(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    """Custom filter tugmalari."""
    parts = call.data.split(":")
    action = parts[1]
    data = await state.get_data()
    filters = data.get("custom_filters", {})

    if action == "apply":
        seg = _custom_to_segment(filters)
        await state.update_data(segment=seg)
        await call.answer("Filter saqlandi", show_alert=True)
        await state.set_state(BroadcastSG.buttons)
        await call.message.edit_reply_markup(reply_markup=broadcast_after_content_kb())
        return

    if action == "refresh":
        target = await _calc_target(session, _custom_to_segment(filters))
        await call.answer(f"Maqsad: {target}", show_alert=True)
        await call.message.edit_reply_markup(
            reply_markup=broadcast_custom_segment_kb(filters, target_count=target)
        )
        return

    # action: active/new/lang/premium, value parts[2]
    value = parts[2]
    filters[action] = value
    await state.update_data(custom_filters=filters)
    target = await _calc_target(session, _custom_to_segment(filters))
    await call.message.edit_reply_markup(
        reply_markup=broadcast_custom_segment_kb(filters, target_count=target)
    )
    await call.answer()


@router.callback_query(F.data == "bc_back_content", BroadcastSG.segment)
async def fsm_bc_back_content(call: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastSG.buttons)
    await call.message.edit_reply_markup(reply_markup=broadcast_after_content_kb())
    await call.answer()


@router.callback_query(F.data == "bc_preview", BroadcastSG.buttons)
async def fsm_bc_preview(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    data = await state.get_data()
    text = data.get("text", "")
    seg = data.get("segment", {"type": "all"})

    target = await _calc_target(session, seg) if session else 0
    seg_label = _segment_label(seg)

    preview = (
        f"📢 <b>Broadcast ko'rik</b>\n\n"
        f"{text}\n\n"
        f"<b>Rejim:</b> {data.get('mode', 'custom')}\n"
        f"<b>Segment:</b> {seg_label}\n"
        f"<b>Maqsad:</b> ~{target} foydalanuvchi"
    )
    media_keys = [k for k in data if k.startswith("media_")]
    if media_keys:
        preview += f"\n<b>Media:</b> {', '.join(k.replace('media_', '') for k in media_keys)}"
    if data.get("buttons"):
        total_btn = sum(len(r) for r in data["buttons"])
        preview += f"\n<b>Tugmalar:</b> {total_btn} ta"

    await call.message.answer(preview, reply_markup=broadcast_confirm_kb())
    await state.set_state(BroadcastSG.preview)
    await call.answer()


def _segment_label(seg: dict) -> str:
    if not seg or seg.get("type") == "all":
        return "🌐 Barchaga"
    t = seg.get("type")
    if t == "premium":
        return "⭐ Premium"
    if t == "active":
        return f"🔥 Faol ({seg.get('days', 7)} kun)"
    if t == "new":
        return f"🆕 Yangi ({seg.get('days', 7)} kun)"
    if t == "custom":
        parts = []
        if seg.get("active_days"):
            parts.append(f"Faol {seg['active_days']}k")
        if seg.get("new_days"):
            parts.append(f"Yangi {seg['new_days']}k")
        if seg.get("lang"):
            parts.append(f"Til {seg['lang']}")
        if seg.get("premium_only"):
            parts.append("Premium")
        if seg.get("non_premium"):
            parts.append("Premium emas")
        return "🎯 " + (", ".join(parts) if parts else "Barchaga")
    return "🌐 Barchaga"


@router.callback_query(F.data == "bc_test", BroadcastSG.preview)
async def fsm_bc_test(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    """Test yuborish — adminning o'ziga."""
    data = await state.get_data()
    try:
        from bot.loader import bot
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb = None
        if data.get("buttons"):
            builder = InlineKeyboardBuilder()
            for row in data["buttons"]:
                row_buttons = []
                for btn in row:
                    if btn.get("url"):
                        row_buttons.append(InlineKeyboardButton(text=btn["text"], url=btn["url"]))
                    elif btn.get("callback_data"):
                        row_buttons.append(InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"]))
                if row_buttons:
                    builder.row(*row_buttons)
            kb = builder.as_markup()

        text = data.get("text", "")
        uid = call.from_user.id
        if data.get("media_video"):
            await bot.send_video(uid, data["media_video"], caption=text, reply_markup=kb)
        elif data.get("media_photo"):
            await bot.send_photo(uid, data["media_photo"], caption=text, reply_markup=kb)
        elif data.get("media_animation"):
            await bot.send_animation(uid, data["media_animation"], caption=text, reply_markup=kb)
        elif data.get("media_document"):
            await bot.send_document(uid, data["media_document"], caption=text, reply_markup=kb)
        elif text:
            await bot.send_message(uid, text, reply_markup=kb)
        else:
            await call.answer("Bo'sh xabar", show_alert=True)
            return
        await call.answer("✅ Test xabar yuborildi", show_alert=True)
    except Exception as e:
        logger.error(f"test send: {e}")
        await call.answer(f"❌ {str(e)[:80]}", show_alert=True)


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
    bc.segment = data.get("segment", {"type": "all"})
    if data.get("buttons"):
        bc.buttons = data["buttons"]
    await session.commit()

    progress_msg = await call.message.edit_text(
        f"🚀 <b>Broadcast #{bc.id} ishga tushirildi...</b>\n\nKutilmoqda...",
        reply_markup=broadcast_controls(bc.id)
    )
    await call.answer()
    await state.clear()

    from services.broadcaster import BroadcastEngine
    from bot.loader import bot
    engine = BroadcastEngine(session, bot)
    asyncio.create_task(engine.start(bc.id, call.from_user.id, progress_chat_id=call.message.chat.id, progress_message_id=progress_msg.message_id))


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
