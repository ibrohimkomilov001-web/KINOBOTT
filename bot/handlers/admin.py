from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.admin_repo import AdminRepository
from db.repositories.channel_repo import ChannelRepository
from db.repositories.user_repo import UserRepository
from db.repositories.movie_repo import MovieRepository
from db.repositories.series_repo import SeriesRepository
from db.repositories.settings_repo import SettingsRepository
from db.constants import AdminRole
from services.stats import StatsService
from bot.keyboards.admin import (
    ADMIN_BUTTONS, admin_main_reply_kb, remove_reply_kb,
    movie_menu_kb, movie_list_kb, movie_detail_kb,
    series_list_kb, series_detail_kb, season_episodes_kb,
    channels_kb, channel_detail_kb,
    broadcast_mode_kb,
    settings_kb, admins_kb, admin_detail_kb,
    confirm_kb, back_kb, skip_kb,
)
from bot.states import (
    AddMovieSG, AddSeriesSG, AddSeasonSG, AddEpisodeSG,
    AddChannelSG, BroadcastSG, AddAdminSG, SettingsSG, AdSG,
)
from config import settings as app_settings
import logging

logger = logging.getLogger(__name__)
router = Router()


# ═══════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════

async def _is_admin(user_id: int, session: AsyncSession, perm: str | None = None) -> bool:
    repo = AdminRepository(session)
    if perm:
        return await repo.has_permission(user_id, perm)
    return await repo.is_admin(user_id)


# ═══════════════════════════════════════════════════════════════
# /admin — Reply Keyboard panel
# ═══════════════════════════════════════════════════════════════

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext, session: AsyncSession | None = None):
    if not session:
        return await message.reply("Xatolik: sessiya topilmadi")
    if not await _is_admin(message.from_user.id, session):
        return await message.reply("Siz admin emassiz.")
    await state.clear()
    repo = AdminRepository(session)
    role = await repo.get_role(message.from_user.id)
    await message.answer(
        f"👨‍💼 <b>Admin paneli</b>\nRolingiz: <code>{role}</code>",
        reply_markup=admin_main_reply_kb()
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(message.from_user.id, session):
        return
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=admin_main_reply_kb())


# ═══════════════════════════════════════════════════════════════
# 📊 Statistika
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == ADMIN_BUTTONS["stats"])
async def btn_stats(message: Message, session: AsyncSession | None = None):
    if not session or not await _is_admin(message.from_user.id, session):
        return
    try:
        svc = StatsService(session)
        d = await svc.get_dashboard_stats()
        top = await svc.get_top_content(limit=5)
        text = (
            "📊 <b>Statistika</b>\n\n"
            f"👥 Jami: <b>{d['total_users']}</b>\n"
            f"📅 Bugun faol: <b>{d['active_today']}</b>\n"
            f"📆 7 kun: <b>{d['active_week']}</b>\n"
            f"🗓 30 kun: <b>{d['active_month']}</b>\n\n"
            f"🆕 Bugun yangi: <b>{d['new_today']}</b>\n"
            f"🆕 7 kun yangi: <b>{d['new_week']}</b>\n\n"
            f"🎬 Kinolar: <b>{d['movies']}</b>\n"
            f"📺 Seriallar: <b>{d['series']}</b>\n\n"
            f"🚫 Ban: {d['banned']} | 🔒 Blok: {d['blocked']} | ⭐ Premium: {d['premium']}"
        )
        if top.get("top_movies"):
            text += "\n\n🔝 <b>Top kinolar:</b>"
            for i, t in enumerate(top["top_movies"][:5]):
                text += f"\n  {i+1}. {t[0]} — {t[1]} ko'rish"
        await message.answer(text)
    except Exception as e:
        logger.error(f"Stats error: {e}")
        await message.answer("❌ Statistika olishda xatolik")


# ═══════════════════════════════════════════════════════════════
# 🎬 Kino boshqaruvi
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == ADMIN_BUTTONS["movies"])
async def btn_movies(message: Message, session: AsyncSession | None = None):
    if not session or not await _is_admin(message.from_user.id, session):
        return
    await message.answer("🎬 <b>Kino boshqaruvi</b>", reply_markup=movie_menu_kb())


@router.callback_query(F.data == "movie_add")
async def cb_movie_add(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_content"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer("🎬 Kino video/faylini yuboring:")
    await state.set_state(AddMovieSG.video)
    await call.answer()


@router.callback_query(F.data.startswith("movie_list:"))
async def cb_movie_list(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    page = int(call.data.split(":")[1])
    repo = MovieRepository(session)
    movies, total_pages = await repo.get_all_paginated(page=page)
    if not movies:
        await call.answer("Kinolar topilmadi", show_alert=True)
        return
    await call.message.edit_text(
        "📋 <b>Kinolar ro'yxati</b>",
        reply_markup=movie_list_kb(movies, page, total_pages)
    )
    await call.answer()


@router.callback_query(F.data.startswith("movie_view:"))
async def cb_movie_view(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    movie_id = int(call.data.split(":")[1])
    repo = MovieRepository(session)
    m = await repo.get_by_id(movie_id)
    if not m:
        return await call.answer("Kino topilmadi", show_alert=True)
    text = (
        f"🎬 <b>{m.title}</b>\n"
        f"Kod: <code>{m.code}</code>\n"
        f"Tavsif: {m.description or '—'}\n"
        f"Ko'rishlar: {m.views}\n"
        f"Reyting: {m.rating_avg or 0:.1f}/5 ({m.rating_count})"
    )
    await call.message.edit_text(text, reply_markup=movie_detail_kb(m.id))
    await call.answer()


@router.callback_query(F.data.startswith("movie_del:"))
async def cb_movie_del(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_content"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    movie_id = int(call.data.split(":")[1])
    repo = MovieRepository(session)
    ok = await repo.delete(movie_id)
    await session.commit()
    if ok:
        await call.answer("✅ Kino o'chirildi", show_alert=True)
    else:
        await call.answer("❌ Xatolik", show_alert=True)
    movies, total_pages = await repo.get_all_paginated(page=0)
    if movies:
        await call.message.edit_text("📋 <b>Kinolar ro'yxati</b>", reply_markup=movie_list_kb(movies, 0, total_pages))
    else:
        await call.message.edit_text("📋 Kinolar topilmadi")


# ═══════════════════════════════════════════════════════════════
# Serial callbacks
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "series_add")
async def cb_series_add(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_content"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer("📺 Serial nomini kiriting:")
    await state.set_state(AddSeriesSG.title)
    await call.answer()


@router.callback_query(F.data.startswith("series_list:"))
async def cb_series_list(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    page = int(call.data.split(":")[1])
    repo = SeriesRepository(session)
    items, total_pages = await repo.get_all_paginated(page=page)
    if not items:
        await call.answer("Seriallar topilmadi", show_alert=True)
        return
    await call.message.edit_text(
        "📋 <b>Seriallar ro'yxati</b>",
        reply_markup=series_list_kb(items, page, total_pages)
    )
    await call.answer()


@router.callback_query(F.data.startswith("series_view:"))
async def cb_series_view(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    sid = int(call.data.split(":")[1])
    repo = SeriesRepository(session)
    s = await repo.get_by_id(sid)
    if not s:
        return await call.answer("Serial topilmadi", show_alert=True)
    seasons = await repo.get_seasons(sid)
    season_text = ""
    for sn in seasons:
        eps = await repo.get_episodes(sn.id)
        season_text += f"\n📂 Sezon {sn.season_number} — {len(eps)} epizod"
    text = (
        f"📺 <b>{s.title}</b>\n"
        f"Kod: <code>{s.code}</code>\n"
        f"Tavsif: {s.description or '—'}\n"
        f"Ko'rishlar: {s.views}{season_text}"
    )
    await call.message.edit_text(text, reply_markup=series_detail_kb(sid))
    await call.answer()


@router.callback_query(F.data.startswith("series_del:"))
async def cb_series_del(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_content"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    sid = int(call.data.split(":")[1])
    repo = SeriesRepository(session)
    ok = await repo.delete(sid)
    await session.commit()
    await call.answer("✅ Serial o'chirildi" if ok else "❌ Xatolik", show_alert=True)
    items, total_pages = await repo.get_all_paginated(page=0)
    if items:
        await call.message.edit_text("📋 <b>Seriallar</b>", reply_markup=series_list_kb(items, 0, total_pages))
    else:
        await call.message.edit_text("📋 Seriallar topilmadi")


# ═══════════════════════════════════════════════════════════════
# 📋 Kanallar
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == ADMIN_BUTTONS["channels"])
async def btn_channels(message: Message, session: AsyncSession | None = None):
    if not session or not await _is_admin(message.from_user.id, session, "manage_channels"):
        return
    repo = ChannelRepository(session)
    chs = await repo.get_all()
    text = "📋 <b>Kanallar</b>" + ("\n\nKanal yo'q" if not chs else "")
    await message.answer(text, reply_markup=channels_kb(chs))


@router.callback_query(F.data == "ch_list")
async def cb_ch_list(call: CallbackQuery, session: AsyncSession | None = None):
    if not session:
        return await call.answer()
    repo = ChannelRepository(session)
    chs = await repo.get_all()
    await call.message.edit_text("📋 <b>Kanallar</b>", reply_markup=channels_kb(chs))
    await call.answer()


@router.callback_query(F.data.startswith("ch_view:"))
async def cb_ch_view(call: CallbackQuery, session: AsyncSession | None = None):
    if not session:
        return await call.answer()
    ch_id = int(call.data.split(":")[1])
    repo = ChannelRepository(session)
    ch = await repo.get_by_id(ch_id)
    if not ch:
        return await call.answer("Kanal topilmadi", show_alert=True)
    req = "Ha ✅" if ch.is_required else "Yo'q ❌"
    text = (
        f"📋 <b>{ch.title}</b>\n"
        f"ID: <code>{ch.tg_chat_id}</code>\n"
        f"Turi: {ch.type}\n"
        f"Majburiy: {req}\n"
        f"A'zolar: {ch.members_count}\n"
        f"Invite: {ch.invite_link or '—'}"
    )
    await call.message.edit_text(text, reply_markup=channel_detail_kb(ch))
    await call.answer()


@router.callback_query(F.data.startswith("ch_toggle:"))
async def cb_ch_toggle(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_channels"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    ch_id = int(call.data.split(":")[1])
    repo = ChannelRepository(session)
    ch = await repo.get_by_id(ch_id)
    if ch:
        await repo.update(ch_id, is_required=not ch.is_required)
        await session.commit()
        status = "yoqildi ✅" if not ch.is_required else "o'chirildi ❌"
        await call.answer(f"Majburiy obuna {status}", show_alert=True)
        ch = await repo.get_by_id(ch_id)
        req = "Ha ✅" if ch.is_required else "Yo'q ❌"
        text = (
            f"📋 <b>{ch.title}</b>\n"
            f"ID: <code>{ch.tg_chat_id}</code>\n"
            f"Turi: {ch.type}\nMajburiy: {req}\n"
            f"A'zolar: {ch.members_count}\nInvite: {ch.invite_link or '—'}"
        )
        await call.message.edit_text(text, reply_markup=channel_detail_kb(ch))
    else:
        await call.answer("Topilmadi", show_alert=True)


@router.callback_query(F.data.startswith("ch_invite:"))
async def cb_ch_invite(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_channels"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    ch_id = int(call.data.split(":")[1])
    repo = ChannelRepository(session)
    ch = await repo.get_by_id(ch_id)
    if not ch:
        return await call.answer("Topilmadi", show_alert=True)
    try:
        from bot.loader import bot
        link = await bot.create_chat_invite_link(ch.tg_chat_id)
        await repo.update(ch_id, invite_link=link.invite_link)
        await session.commit()
        await call.answer(f"✅ Invite link yangilandi", show_alert=True)
    except Exception as e:
        logger.error(f"Invite link error: {e}")
        await call.answer(f"❌ Xatolik: {str(e)[:100]}", show_alert=True)


@router.callback_query(F.data.startswith("ch_del:"))
async def cb_ch_del(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_channels"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    ch_id = int(call.data.split(":")[1])
    repo = ChannelRepository(session)
    ok = await repo.delete(ch_id)
    await session.commit()
    await call.answer("✅ Kanal o'chirildi" if ok else "❌ Xatolik", show_alert=True)
    chs = await repo.get_all()
    await call.message.edit_text("📋 <b>Kanallar</b>", reply_markup=channels_kb(chs))


@router.callback_query(F.data == "ch_add")
async def cb_ch_add(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_channels"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer(
        "Kanal/guruh Telegram chat ID sini yuboring\n"
        "(masalan: <code>-1001234567890</code>)\n\n"
        "Bot kanalda admin bo'lishi kerak!"
    )
    await state.set_state(AddChannelSG.chat_id)
    await call.answer()


# ═══════════════════════════════════════════════════════════════
# 📢 Xabar yuborish (Broadcast)
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == ADMIN_BUTTONS["broadcast"])
async def btn_broadcast(message: Message, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(message.from_user.id, session, "broadcast"):
        return
    await message.answer("📢 <b>Xabar yuborish</b>\n\nRejimni tanlang:", reply_markup=broadcast_mode_kb())
    await state.set_state(BroadcastSG.mode)


# ═══════════════════════════════════════════════════════════════
# ⚙️ Sozlamalar
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == ADMIN_BUTTONS["settings"])
async def btn_settings(message: Message, session: AsyncSession | None = None):
    if not session or not await _is_admin(message.from_user.id, session):
        return
    repo = SettingsRepository(session)
    auto_code = await repo.get_bool("auto_code", True)
    force_sub = await repo.get_bool("force_subscription", True)
    maintenance = await repo.get_bool("maintenance_mode", False)
    await message.answer("⚙️ <b>Sozlamalar</b>", reply_markup=settings_kb(auto_code, force_sub, maintenance))


@router.callback_query(F.data == "admin:settings")
async def cb_admin_settings(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    repo = SettingsRepository(session)
    auto_code = await repo.get_bool("auto_code", True)
    force_sub = await repo.get_bool("force_subscription", True)
    maintenance = await repo.get_bool("maintenance_mode", False)
    await call.message.edit_text("⚙️ <b>Sozlamalar</b>", reply_markup=settings_kb(auto_code, force_sub, maintenance))
    await call.answer()


@router.callback_query(F.data.startswith("set_toggle:"))
async def cb_set_toggle(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    key = call.data.split(":")[1]
    repo = SettingsRepository(session)
    current = await repo.get_bool(key, False)
    await repo.set(key, str(not current).lower())
    await session.commit()
    status = "yoqildi 🟢" if not current else "o'chirildi 🔴"
    await call.answer(f"{key}: {status}", show_alert=True)
    auto_code = await repo.get_bool("auto_code", True)
    force_sub = await repo.get_bool("force_subscription", True)
    maintenance = await repo.get_bool("maintenance_mode", False)
    await call.message.edit_reply_markup(reply_markup=settings_kb(auto_code, force_sub, maintenance))


@router.callback_query(F.data == "set_bc_rate")
async def cb_set_bc_rate(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer("Broadcast tezligini kiriting (1-30 msg/sec):")
    await state.set_state(SettingsSG.broadcast_rate)
    await call.answer()


@router.callback_query(F.data == "set_base_channel")
async def cb_set_base_channel(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer("Baza kanal ID ni kiriting (masalan: -1001234567890):")
    await state.set_state(SettingsSG.base_channel)
    await call.answer()


@router.callback_query(F.data == "set_backup")
async def cb_set_backup(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "backup"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    try:
        from services.backup import BackupService
        from bot.loader import bot
        svc = BackupService(session)
        path = await svc.backup_now()
        if path:
            from aiogram.types import FSInputFile
            await bot.send_document(call.from_user.id, FSInputFile(path), caption="💾 Backup tayyor")
            await call.answer("✅ Backup yaratildi", show_alert=True)
        else:
            await call.answer("❌ Backup xatolik", show_alert=True)
    except Exception as e:
        logger.error(f"Backup error: {e}")
        await call.answer(f"❌ {str(e)[:100]}", show_alert=True)


@router.callback_query(F.data == "set_restore")
async def cb_set_restore(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "backup"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer("📥 Backup faylini (.json.gz) yuboring:")
    await state.set_state(SettingsSG.restore_file)
    await call.answer()


# ═══════════════════════════════════════════════════════════════
# 👥 Adminlar
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == ADMIN_BUTTONS["admins"])
async def btn_admins(message: Message, session: AsyncSession | None = None):
    if not session or not await _is_admin(message.from_user.id, session, "manage_admins"):
        return
    repo = AdminRepository(session)
    adms = await repo.get_all_admins()
    await message.answer("👥 <b>Adminlar</b>", reply_markup=admins_kb(adms))


@router.callback_query(F.data == "adm_list")
async def cb_adm_list(call: CallbackQuery, session: AsyncSession | None = None):
    if not session:
        return await call.answer()
    repo = AdminRepository(session)
    adms = await repo.get_all_admins()
    await call.message.edit_text("👥 <b>Adminlar</b>", reply_markup=admins_kb(adms))
    await call.answer()


@router.callback_query(F.data == "adm_add")
async def cb_adm_add(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_admins"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer(
        "Yangi admin:\n"
        "Format: <code>USER_ID rol</code>\n"
        "Rollar: owner, admin, content_mgr, broadcaster\n"
        "Masalan: <code>123456789 admin</code>"
    )
    await state.set_state(AddAdminSG.user_input)
    await call.answer()


@router.callback_query(F.data.startswith("adm_del:"))
async def cb_adm_del(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_admins"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    uid = int(call.data.split(":")[1])
    repo = AdminRepository(session)
    admin_obj = await repo.get_by_user_id(uid)
    if admin_obj:
        await session.delete(admin_obj)
        await session.commit()
        await call.answer("✅ Admin o'chirildi", show_alert=True)
    else:
        await call.answer("Topilmadi", show_alert=True)
    adms = await repo.get_all_admins()
    await call.message.edit_text("👥 <b>Adminlar</b>", reply_markup=admins_kb(adms))


# ═══════════════════════════════════════════════════════════════
# 📣 Reklama boshqaruvi
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "set_ads")
async def cb_ads_list(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    from db.repositories.ad_repo import AdRepository
    repo = AdRepository(session)
    ads = await repo.get_all(limit=20)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    lines = ["📣 <b>Reklamalar</b>\n"]
    if ads:
        for ad in ads:
            status = "🟢" if ad.is_active else "🔴"
            lines.append(f"{status} #{ad.id} — ko'rishlar: {ad.views_count} / kliklar: {ad.clicks_count}")
        for ad in ads[:10]:
            label = "🟢" if ad.is_active else "🔴"
            builder.row(
                InlineKeyboardButton(text=f"{label} #{ad.id}", callback_data=f"ad_toggle:{ad.id}"),
                InlineKeyboardButton(text="🗑", callback_data=f"ad_del:{ad.id}"),
            )
    else:
        lines.append("Reklamalar yo'q")
    builder.row(InlineKeyboardButton(text="➕ Reklama yaratish", callback_data="ad_create"))
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:settings"))
    await call.message.edit_text("\n".join(lines), reply_markup=builder.as_markup())
    await call.answer()


@router.callback_query(F.data == "ad_create")
async def cb_ad_create(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer("📣 Reklama matnini yoki media (rasm/video) yuboring:")
    await state.set_state(AdSG.content)
    await call.answer()


@router.callback_query(F.data.startswith("ad_toggle:"))
async def cb_ad_toggle(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    ad_id = int(call.data.split(":")[1])
    from db.repositories.ad_repo import AdRepository
    repo = AdRepository(session)
    ad = await repo.toggle_active(ad_id)
    await session.commit()
    if ad:
        s = "yoqildi 🟢" if ad.is_active else "o'chirildi 🔴"
        await call.answer(f"Reklama #{ad_id} {s}", show_alert=True)
    else:
        await call.answer("Topilmadi", show_alert=True)


@router.callback_query(F.data.startswith("ad_del:"))
async def cb_ad_del(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    ad_id = int(call.data.split(":")[1])
    from db.repositories.ad_repo import AdRepository
    repo = AdRepository(session)
    ok = await repo.delete(ad_id)
    await session.commit()
    if ok:
        await call.answer("✅ O'chirildi", show_alert=True)
    else:
        await call.answer("Topilmadi", show_alert=True)


# ═══════════════════════════════════════════════════════════════
# Broadcast boshqaruvi (pauza/stop)
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("bc_pause:"))
async def cb_bc_pause(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "broadcast"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    bc_id = int(call.data.split(":")[1])
    from db.repositories.broadcast_repo import BroadcastRepository
    repo = BroadcastRepository(session)
    await repo.pause_broadcast(bc_id)
    await session.commit()
    await call.answer("⏸ Broadcast pauzaga olindi", show_alert=True)


@router.callback_query(F.data.startswith("bc_stop:"))
async def cb_bc_stop(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "broadcast"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    bc_id = int(call.data.split(":")[1])
    from db.repositories.broadcast_repo import BroadcastRepository
    repo = BroadcastRepository(session)
    await repo.fail_broadcast(bc_id)
    await session.commit()
    await call.answer("❌ Broadcast to'xtatildi", show_alert=True)
    await call.message.edit_text(f"❌ Broadcast #{bc_id} to'xtatildi.")


# ═══════════════════════════════════════════════════════════════
# noop callback (paginatsiya uchun)
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()
