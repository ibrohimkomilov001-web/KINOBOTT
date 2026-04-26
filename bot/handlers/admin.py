from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.admin_repo import AdminRepository
from db.repositories.channel_repo import ChannelRepository
from db.repositories.user_repo import UserRepository
from db.repositories.movie_repo import MovieRepository
from db.repositories.series_repo import SeriesRepository
from db.repositories.settings_repo import SettingsRepository
from db.repositories.broadcast_repo import BroadcastRepository
from db.constants import AdminRole
from services.stats import StatsService
from bot.keyboards.admin import (
    ADMIN_BUTTONS, admin_main_reply_kb, remove_reply_kb,
    movie_menu_kb, movie_list_kb, movie_detail_kb, movie_edit_kb,
    series_list_kb, series_detail_kb, series_edit_kb, season_episodes_kb,
    channels_kb, channel_detail_kb, channel_type_kb,
    broadcast_mode_kb, broadcast_history_kb,
    settings_kb, admins_kb, admin_detail_kb,
    stats_kb, confirm_kb, back_kb, skip_kb,
)
from bot.states import (
    AddMovieSG, AddSeriesSG, AddSeasonSG, AddEpisodeSG,
    AddChannelSG, BroadcastSG, AddAdminSG, SettingsSG,
    EditMovieSG, EditSeriesSG, SearchMovieSG,
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


@router.callback_query(F.data == "admin_close")
async def cb_admin_close(call: CallbackQuery):
    """Yopish — xabarni o'chirish."""
    try:
        await call.message.delete()
    except Exception:
        await call.message.edit_text("✅ Yopildi")
    await call.answer()


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
        await message.answer(text, reply_markup=stats_kb())
    except Exception as e:
        logger.error(f"Stats error: {e}")
        await message.answer("❌ Statistika olishda xatolik")


@router.callback_query(F.data == "stats_top")
async def cb_stats_top(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    try:
        svc = StatsService(session)
        top = await svc.get_top_content(limit=10)
        lines = ["🔝 <b>Top kontent</b>\n"]
        if top.get("top_movies"):
            lines.append("\n🎬 <b>Kinolar:</b>")
            for i, t in enumerate(top["top_movies"][:10]):
                lines.append(f"  {i+1}. {t[0]} — {t[1]} ko'rish")
        if top.get("top_series"):
            lines.append("\n📺 <b>Seriallar:</b>")
            for i, t in enumerate(top["top_series"][:10]):
                lines.append(f"  {i+1}. {t[0]} — {t[1]} ko'rish")
        await call.message.answer("\n".join(lines))
    except Exception as e:
        logger.error(f"stats_top: {e}")
    await call.answer()


@router.callback_query(F.data == "stats_search")
async def cb_stats_search(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    try:
        from db.repositories.stats_repo import StatsRepository
        repo = StatsRepository(session)
        top = await repo.get_top_searches(limit=15)
        lines = ["📉 <b>Top qidiruvlar</b>\n"]
        for i, (q, c) in enumerate(top):
            lines.append(f"  {i+1}. <code>{q}</code> — {c} marta")
        if not top:
            lines.append("Ma'lumot yo'q")
        await call.message.answer("\n".join(lines))
    except Exception as e:
        logger.error(f"stats_search: {e}")
        await call.answer("Xatolik", show_alert=True)
        return
    await call.answer()


@router.callback_query(F.data == "stats_channels")
async def cb_stats_channels(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    repo = ChannelRepository(session)
    chs = await repo.get_all()
    lines = ["👥 <b>Kanallar statistikasi</b>\n"]
    for ch in chs:
        ref = await repo.get_referral_count(ch.id)
        type_emoji = {"public": "📢", "private": "🔒", "request_join": "✋"}.get(ch.type, "📋")
        lines.append(f"{type_emoji} <b>{ch.title}</b> — a'zo: {ch.members_count}, referral: {ref}")
    if not chs:
        lines.append("Kanal yo'q")
    await call.message.answer("\n".join(lines))
    await call.answer()


@router.callback_query(F.data == "stats_export")
async def cb_stats_export(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    try:
        import csv
        import io
        from aiogram.types import BufferedInputFile
        svc = StatsService(session)
        d = await svc.get_dashboard_stats()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["metric", "value"])
        for k, v in d.items():
            writer.writerow([k, v])
        data = buf.getvalue().encode("utf-8")
        await call.message.answer_document(
            BufferedInputFile(data, filename="stats.csv"),
            caption="📊 Statistika eksport"
        )
    except Exception as e:
        logger.error(f"stats_export: {e}")
        await call.answer(f"❌ {str(e)[:80]}", show_alert=True)
        return
    await call.answer("✅ Tayyor")


# ═══════════════════════════════════════════════════════════════
# 🎬 Kino boshqaruvi
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == ADMIN_BUTTONS["movies"])
async def btn_movies(message: Message, session: AsyncSession | None = None):
    if not session or not await _is_admin(message.from_user.id, session):
        return
    await message.answer("🎬 <b>Kino boshqaruvi</b>", reply_markup=movie_menu_kb())


@router.callback_query(F.data == "movie_menu")
async def cb_movie_menu(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.edit_text("🎬 <b>Kino boshqaruvi</b>", reply_markup=movie_menu_kb())
    await call.answer()


@router.callback_query(F.data == "movie_add")
async def cb_movie_add(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_content"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer("🎬 Kino video/faylini yuboring:")
    await state.set_state(AddMovieSG.video)
    await call.answer()


@router.callback_query(F.data == "movie_search")
async def cb_movie_search(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer("🔍 Qidiruv so'zini yuboring (nom yoki kod):")
    await state.set_state(SearchMovieSG.query)
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
    genres = ", ".join(m.genres) if m.genres else "—"
    text = (
        f"🎬 <b>{m.title}</b>\n"
        f"Kod: <code>{m.code}</code>\n"
        f"Yil: {m.year or '—'}\n"
        f"Janrlar: {genres}\n"
        f"Tavsif: {m.description or '—'}\n\n"
        f"👁 Ko'rishlar: {m.views}\n"
        f"⭐ Reyting: {m.rating_avg or 0:.1f}/5 ({m.rating_count})"
    )
    try:
        await call.message.edit_text(text, reply_markup=movie_detail_kb(m.id))
    except Exception:
        await call.message.answer(text, reply_markup=movie_detail_kb(m.id))
    await call.answer()


@router.callback_query(F.data.startswith("movie_edit:"))
async def cb_movie_edit(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_content"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    movie_id = int(call.data.split(":")[1])
    await call.message.edit_text(
        "📝 <b>Tahrirlash</b>\n\nQaysi maydonni o'zgartirasiz?",
        reply_markup=movie_edit_kb(movie_id)
    )
    await call.answer()


@router.callback_query(F.data.startswith("medit:"))
async def cb_medit_field(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_content"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    parts = call.data.split(":")
    movie_id, field = int(parts[1]), parts[2]
    await state.set_state(EditMovieSG.value)
    await state.update_data(movie_id=movie_id, field=field)
    prompts = {
        "title": "Yangi nomni yuboring:",
        "description": "Yangi tavsifni yuboring:",
        "genres": "Yangi janrlarni yuboring (vergul bilan ajrating):",
        "year": "Yangi yilni yuboring (raqam):",
        "video": "Yangi videoni yuboring:",
        "code": "Yangi kodni yuboring:",
    }
    await call.message.answer(prompts.get(field, "Yangi qiymatni yuboring:"))
    await call.answer()


@router.callback_query(F.data.startswith("movie_resend:"))
async def cb_movie_resend(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_content"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    movie_id = int(call.data.split(":")[1])
    repo = MovieRepository(session)
    m = await repo.get_by_id(movie_id)
    if not m:
        return await call.answer("Topilmadi", show_alert=True)
    try:
        from bot.loader import bot
        base_ch = app_settings.BASE_CHANNEL_ID
        if not base_ch:
            srepo = SettingsRepository(session)
            base_ch_str = await srepo.get("base_channel_id")
            base_ch = int(base_ch_str) if base_ch_str else None
        if not base_ch:
            return await call.answer("Baza kanal sozlanmagan", show_alert=True)
        await bot.send_video(base_ch, m.video_file_id, caption=f"🎬 {m.title}\nKod: {m.code}")
        await call.answer("✅ Yuborildi", show_alert=True)
    except Exception as e:
        logger.error(f"resend: {e}")
        await call.answer(f"❌ {str(e)[:80]}", show_alert=True)


@router.callback_query(F.data.startswith("movie_stats:"))
async def cb_movie_stats(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    movie_id = int(call.data.split(":")[1])
    repo = MovieRepository(session)
    m = await repo.get_by_id(movie_id)
    if not m:
        return await call.answer("Topilmadi", show_alert=True)
    text = (
        f"📊 <b>{m.title}</b> statistika\n\n"
        f"👁 Ko'rishlar: {m.views}\n"
        f"⭐ Reyting: {m.rating_avg or 0:.2f}/5\n"
        f"🗳 Ovozlar: {m.rating_count}\n"
        f"📅 Yaratilgan: {m.created_at.strftime('%Y-%m-%d')}"
    )
    await call.message.answer(text)
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
        await call.message.edit_text("📋 Kinolar topilmadi", reply_markup=movie_menu_kb())


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
    genres = ", ".join(s.genres) if s.genres else "—"
    text = (
        f"📺 <b>{s.title}</b>\n"
        f"Kod: <code>{s.code}</code>\n"
        f"Yil: {s.year or '—'}\n"
        f"Janrlar: {genres}\n"
        f"Tavsif: {s.description or '—'}\n"
        f"👁 Ko'rishlar: {s.views}{season_text}"
    )
    try:
        await call.message.edit_text(text, reply_markup=series_detail_kb(sid))
    except Exception:
        await call.message.answer(text, reply_markup=series_detail_kb(sid))
    await call.answer()


@router.callback_query(F.data.startswith("series_edit:"))
async def cb_series_edit(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_content"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    sid = int(call.data.split(":")[1])
    await call.message.edit_text(
        "📝 <b>Tahrirlash</b>\n\nQaysi maydonni o'zgartirasiz?",
        reply_markup=series_edit_kb(sid)
    )
    await call.answer()


@router.callback_query(F.data.startswith("sedit:"))
async def cb_sedit_field(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_content"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    parts = call.data.split(":")
    series_id, field = int(parts[1]), parts[2]
    await state.set_state(EditSeriesSG.value)
    await state.update_data(series_id=series_id, field=field)
    prompts = {
        "title": "Yangi nomni yuboring:",
        "description": "Yangi tavsifni yuboring:",
        "genres": "Yangi janrlarni yuboring (vergul bilan):",
        "year": "Yangi yilni yuboring (raqam):",
        "code": "Yangi kodni yuboring:",
    }
    await call.message.answer(prompts.get(field, "Yangi qiymatni yuboring:"))
    await call.answer()


@router.callback_query(F.data.startswith("series_stats:"))
async def cb_series_stats(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    sid = int(call.data.split(":")[1])
    repo = SeriesRepository(session)
    s = await repo.get_by_id(sid)
    if not s:
        return await call.answer("Topilmadi", show_alert=True)
    seasons = await repo.get_seasons(sid)
    total_eps = 0
    for sn in seasons:
        eps = await repo.get_episodes(sn.id)
        total_eps += len(eps)
    text = (
        f"📊 <b>{s.title}</b> statistika\n\n"
        f"👁 Ko'rishlar: {s.views}\n"
        f"⭐ Reyting: {s.rating_avg or 0:.2f}/5\n"
        f"🗳 Ovozlar: {s.rating_count}\n"
        f"📂 Sezonlar: {len(seasons)}\n"
        f"📺 Epizodlar: {total_eps}"
    )
    await call.message.answer(text)
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
        await call.message.edit_text("📋 Seriallar topilmadi", reply_markup=movie_menu_kb())


# ═══════════════════════════════════════════════════════════════
# 🔗 Kanallar
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == ADMIN_BUTTONS["channels"])
async def btn_channels(message: Message, session: AsyncSession | None = None):
    if not session or not await _is_admin(message.from_user.id, session, "manage_channels"):
        return
    repo = ChannelRepository(session)
    chs = await repo.get_all()
    text = "🔗 <b>Kanallar</b>" + ("\n\nKanal yo'q" if not chs else f"\n\nJami: {len(chs)} ta")
    await message.answer(text, reply_markup=channels_kb(chs))


@router.callback_query(F.data == "ch_list")
async def cb_ch_list(call: CallbackQuery, session: AsyncSession | None = None):
    if not session:
        return await call.answer()
    repo = ChannelRepository(session)
    chs = await repo.get_all()
    text = "🔗 <b>Kanallar</b>" + (f"\n\nJami: {len(chs)} ta" if chs else "\n\nKanal yo'q")
    await call.message.edit_text(text, reply_markup=channels_kb(chs))
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
    type_label = {"public": "📢 Oddiy", "private": "🔒 Yopiq", "request_join": "✋ So'rovli"}.get(ch.type, "📋 Boshqa")
    req = "Ha ✅" if ch.is_required else "Yo'q ❌"
    text = (
        f"📋 <b>{ch.title}</b>\n\n"
        f"ID: <code>{ch.tg_chat_id}</code>\n"
        f"Turi: {type_label}\n"
        f"Majburiy: {req}\n"
        f"A'zolar: {ch.members_count}\n"
        f"Link: {ch.invite_link or '—'}"
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
    if not ch:
        return await call.answer("Topilmadi", show_alert=True)
    new_val = not ch.is_required
    await repo.update(ch_id, is_required=new_val)
    await session.commit()
    status = "yoqildi ✅" if new_val else "o'chirildi ❌"
    await call.answer(f"Majburiy obuna {status}", show_alert=True)
    ch = await repo.get_by_id(ch_id)
    type_label = {"public": "📢 Oddiy", "private": "🔒 Yopiq", "request_join": "✋ So'rovli"}.get(ch.type, "📋")
    req = "Ha ✅" if ch.is_required else "Yo'q ❌"
    text = (
        f"📋 <b>{ch.title}</b>\n\n"
        f"ID: <code>{ch.tg_chat_id}</code>\n"
        f"Turi: {type_label}\nMajburiy: {req}\n"
        f"A'zolar: {ch.members_count}\nLink: {ch.invite_link or '—'}"
    )
    await call.message.edit_text(text, reply_markup=channel_detail_kb(ch))


@router.callback_query(F.data.startswith("ch_link:"))
async def cb_ch_link(call: CallbackQuery, session: AsyncSession | None = None):
    """Linkni ko'rsatish — auto yaratish YO'Q, faqat saqlangan link."""
    if not session or not await _is_admin(call.from_user.id, session, "manage_channels"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    ch_id = int(call.data.split(":")[1])
    repo = ChannelRepository(session)
    ch = await repo.get_by_id(ch_id)
    if not ch:
        return await call.answer("Topilmadi", show_alert=True)
    if ch.invite_link:
        await call.answer(ch.invite_link, show_alert=True)
    else:
        await call.answer("Link saqlanmagan", show_alert=True)


@router.callback_query(F.data.startswith("ch_stats:"))
async def cb_ch_stats(call: CallbackQuery, session: AsyncSession | None = None):
    if not session:
        return await call.answer()
    ch_id = int(call.data.split(":")[1])
    repo = ChannelRepository(session)
    ch = await repo.get_by_id(ch_id)
    if not ch:
        return await call.answer("Topilmadi", show_alert=True)
    refs = await repo.get_referral_count(ch_id)
    text = (
        f"📊 <b>{ch.title}</b> statistika\n\n"
        f"A'zolar (Telegram): {ch.members_count}\n"
        f"Bot orqali kirgan: {refs}\n"
        f"Yaratilgan: {ch.created_at.strftime('%Y-%m-%d')}"
    )
    await call.message.answer(text)
    await call.answer()


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
    text = "🔗 <b>Kanallar</b>" + (f"\n\nJami: {len(chs)} ta" if chs else "\n\nKanal yo'q")
    await call.message.edit_text(text, reply_markup=channels_kb(chs))


@router.callback_query(F.data == "ch_add")
async def cb_ch_add(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_channels"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await state.set_state(AddChannelSG.channel_type)
    await call.message.edit_text(
        "🆕 <b>Kanal turini tanlang:</b>\n\n"
        "📢 <b>Oddiy</b> — public kanal (@username)\n"
        "🔒 <b>Yopiq</b> — invite link bilan oddiy yopiq kanal\n"
        "✋ <b>So'rovli</b> — Join Request talab qiladigan kanal/guruh",
        reply_markup=channel_type_kb()
    )
    await call.answer()


@router.callback_query(F.data == "ch_cancel")
async def cb_ch_cancel(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    await state.clear()
    if session:
        repo = ChannelRepository(session)
        chs = await repo.get_all()
        text = "🔗 <b>Kanallar</b>" + (f"\n\nJami: {len(chs)} ta" if chs else "\n\nKanal yo'q")
        await call.message.edit_text(text, reply_markup=channels_kb(chs))
    await call.answer("Bekor qilindi")


# ═══════════════════════════════════════════════════════════════
# 📢 Xabar yuborish (Broadcast)
# ═══════════════════════════════════════════════════════════════

@router.message(F.text == ADMIN_BUTTONS["broadcast"])
async def btn_broadcast(message: Message, state: FSMContext, session: AsyncSession | None = None):
    if not session or not await _is_admin(message.from_user.id, session, "broadcast"):
        return
    await message.answer(
        "📢 <b>Xabar yuborish</b>\n\nRejimni tanlang:",
        reply_markup=broadcast_mode_kb()
    )
    await state.set_state(BroadcastSG.mode)


@router.callback_query(F.data == "bc_back_mode")
async def cb_bc_back_mode(call: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastSG.mode)
    await call.message.edit_text(
        "📢 <b>Xabar yuborish</b>\n\nRejimni tanlang:",
        reply_markup=broadcast_mode_kb()
    )
    await call.answer()


@router.callback_query(F.data == "bc_history")
async def cb_bc_history(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "broadcast"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    repo = BroadcastRepository(session)
    items = await repo.get_recent(limit=20) if hasattr(repo, "get_recent") else []
    if not items:
        await call.answer("Tarix bo'sh", show_alert=True)
        return
    lines = ["📜 <b>Broadcast tarixi (oxirgi 20)</b>\n"]
    for bc in items:
        emoji = {"completed": "✅", "running": "🚀", "paused": "⏸", "failed": "❌", "draft": "📝"}.get(bc.status, "❓")
        date = bc.created_at.strftime("%m-%d %H:%M")
        lines.append(f"{emoji} #{bc.id} | {date} | {bc.sent_count}/{bc.target_count}")
    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=broadcast_history_kb(items)
    )
    await call.answer()


@router.callback_query(F.data.startswith("bc_info:"))
async def cb_bc_info(call: CallbackQuery, session: AsyncSession | None = None):
    if not session:
        return await call.answer()
    bc_id = int(call.data.split(":")[1])
    repo = BroadcastRepository(session)
    bc = await repo.get_by_id(bc_id)
    if not bc:
        return await call.answer("Topilmadi", show_alert=True)
    text = (
        f"📜 <b>Broadcast #{bc.id}</b>\n\n"
        f"Holati: <code>{bc.status}</code>\n"
        f"Rejim: {bc.mode}\n"
        f"Maqsad: {bc.target_count}\n"
        f"Yuborildi: {bc.sent_count}\n"
        f"Xato: {bc.failed_count}\n"
        f"Block: {bc.blocked_count}\n"
        f"Yaratilgan: {bc.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"Yakunlandi: {bc.completed_at.strftime('%Y-%m-%d %H:%M') if bc.completed_at else '—'}\n\n"
        f"Matn: {(bc.text or '—')[:300]}"
    )
    await call.message.answer(text)
    await call.answer()


@router.callback_query(F.data == "bc_export")
async def cb_bc_export(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "broadcast"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    try:
        import csv
        import io
        from aiogram.types import BufferedInputFile
        repo = BroadcastRepository(session)
        items = await repo.get_recent(limit=200) if hasattr(repo, "get_recent") else []
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "status", "mode", "admin_id", "target", "sent", "failed", "blocked", "created", "completed"])
        for bc in items:
            writer.writerow([
                bc.id, bc.status, bc.mode, bc.admin_id,
                bc.target_count, bc.sent_count, bc.failed_count, bc.blocked_count,
                bc.created_at.isoformat(),
                bc.completed_at.isoformat() if bc.completed_at else "",
            ])
        data = buf.getvalue().encode("utf-8")
        await call.message.answer_document(
            BufferedInputFile(data, filename="broadcasts.csv"),
            caption="📤 Broadcast tarixi"
        )
        await call.answer("✅ Tayyor")
    except Exception as e:
        logger.error(f"bc_export: {e}")
        await call.answer(f"❌ {str(e)[:80]}", show_alert=True)


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
# 👥 Adminlar (Sozlamalar ichida)
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:list")
async def cb_admin_list(call: CallbackQuery, session: AsyncSession | None = None):
    """Sozlamalardan kirgich."""
    if not session or not await _is_admin(call.from_user.id, session, "manage_admins"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    repo = AdminRepository(session)
    adms = await repo.get_all_admins()
    await call.message.edit_text("👥 <b>Adminlar</b>", reply_markup=admins_kb(adms))
    await call.answer()


@router.callback_query(F.data == "adm_list")
async def cb_adm_list(call: CallbackQuery, session: AsyncSession | None = None):
    if not session:
        return await call.answer()
    repo = AdminRepository(session)
    adms = await repo.get_all_admins()
    await call.message.edit_text("👥 <b>Adminlar</b>", reply_markup=admins_kb(adms))
    await call.answer()


@router.callback_query(F.data.startswith("adm_view:"))
async def cb_adm_view(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "manage_admins"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    uid = int(call.data.split(":")[1])
    repo = AdminRepository(session)
    a = await repo.get_by_user_id(uid)
    if not a:
        return await call.answer("Topilmadi", show_alert=True)
    text = (
        f"👤 <b>Admin tafsilot</b>\n\n"
        f"User ID: <code>{a.user_id}</code>\n"
        f"Rol: <code>{a.role}</code>\n"
        f"Qo'shilgan: {a.created_at.strftime('%Y-%m-%d')}"
    )
    await call.message.edit_text(text, reply_markup=admin_detail_kb(uid))
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
# Broadcast boshqaruvi (pauza/resume/stop)
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("bc_pause:"))
async def cb_bc_pause(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "broadcast"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    bc_id = int(call.data.split(":")[1])
    repo = BroadcastRepository(session)
    await repo.pause_broadcast(bc_id)
    await session.commit()
    await call.answer("⏸ Broadcast pauzaga olindi", show_alert=True)


@router.callback_query(F.data.startswith("bc_resume:"))
async def cb_bc_resume(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "broadcast"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    bc_id = int(call.data.split(":")[1])
    repo = BroadcastRepository(session)
    await repo.resume_broadcast(bc_id)
    await session.commit()
    await call.answer("▶️ Davom etmoqda", show_alert=True)


@router.callback_query(F.data.startswith("bc_stop:"))
async def cb_bc_stop(call: CallbackQuery, session: AsyncSession | None = None):
    if not session or not await _is_admin(call.from_user.id, session, "broadcast"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    bc_id = int(call.data.split(":")[1])
    repo = BroadcastRepository(session)
    await repo.fail_broadcast(bc_id)
    await session.commit()
    await call.answer("❌ Broadcast to'xtatildi", show_alert=True)
    try:
        await call.message.edit_text(f"❌ Broadcast #{bc_id} to'xtatildi.")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# noop callback (paginatsiya/sarlavha uchun)
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()
