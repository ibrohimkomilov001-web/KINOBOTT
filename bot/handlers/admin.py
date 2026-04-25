from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.admin_repo import AdminRepository
from db.repositories.channel_repo import ChannelRepository
from db.repositories.user_repo import UserRepository
from db.constants import AdminRole
from services.stats import StatsService
from bot.keyboards.admin import admin_main_kb
from bot.states import AddChannelSG, BroadcastSG, AddAdminSG
import logging

logger = logging.getLogger(__name__)
router = Router()


# ─── Helper: check admin ────────────────────────────────────────────────────
async def _check_admin(user_id: int, session: AsyncSession, permission: str | None = None) -> bool:
    admin_repo = AdminRepository(session)
    if permission:
        return await admin_repo.has_permission(user_id, permission)
    return await admin_repo.is_admin(user_id)


# ─── /admin command ─────────────────────────────────────────────────────────
@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession | None = None):
    """Admin panel entry point."""
    if not session:
        return await message.reply("Xatolik: sessiya topilmadi")

    if not await _check_admin(message.from_user.id, session):
        return await message.reply("Siz admin emassiz.")

    admin_repo = AdminRepository(session)
    role = await admin_repo.get_role(message.from_user.id)
    text = f"👨‍💼 <b>Admin paneli</b>\n\nRolingiz: <code>{role}</code>"
    await message.answer(text, reply_markup=admin_main_kb())


# ─── Stats callback ─────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery, session: AsyncSession | None = None):
    """Show dashboard statistics."""
    if not session or not await _check_admin(call.from_user.id, session):
        return await call.answer("Ruxsat yo'q", show_alert=True)

    try:
        stats = StatsService(session)
        d = await stats.get_dashboard_stats()
        text = (
            "📊 <b>Statistika</b>\n\n"
            f"👥 Jami: {d['total_users']}\n"
            f"📅 Bugun faol: {d['active_today']}\n"
            f"📆 7 kun: {d['active_week']}\n"
            f"🗓 30 kun: {d['active_month']}\n\n"
            f"🆕 Bugun yangi: {d['new_today']}\n"
            f"🆕 7 kun yangi: {d['new_week']}\n\n"
            f"🎬 Kinolar: {d['movies']}\n"
            f"📺 Seriallar: {d['series']}\n\n"
            f"🚫 Ban: {d['banned']}\n"
            f"🔒 Blok: {d['blocked']}\n"
            f"⭐ Premium: {d['premium']}"
        )
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")]
        ])
        await call.message.edit_text(text, reply_markup=back_kb)
    except Exception as e:
        logger.error(f"Stats error: {e}")
        await call.answer("Statistika olishda xatolik", show_alert=True)
    await call.answer()


# ─── Admin back to panel ────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_back")
async def cb_admin_back(call: CallbackQuery, session: AsyncSession | None = None):
    if not session:
        return await call.answer()
    admin_repo = AdminRepository(session)
    role = await admin_repo.get_role(call.from_user.id)
    text = f"👨‍💼 <b>Admin paneli</b>\n\nRolingiz: <code>{role}</code>"
    await call.message.edit_text(text, reply_markup=admin_main_kb())
    await call.answer()


# ─── Channel management ─────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_channels")
async def cb_admin_channels(call: CallbackQuery, session: AsyncSession | None = None):
    """Show channel list."""
    if not session or not await _check_admin(call.from_user.id, session, "manage_channels"):
        return await call.answer("Ruxsat yo'q", show_alert=True)

    channel_repo = ChannelRepository(session)
    channels = await channel_repo.get_all()

    if not channels:
        text = "📋 <b>Kanallar</b>\n\nHozircha kanal qo'shilmagan."
    else:
        lines = ["📋 <b>Kanallar</b>\n"]
        for ch in channels:
            req = "✅" if ch.is_required else "❌"
            lines.append(f"  {req} <b>{ch.title}</b> ({ch.type}) — ID: {ch.tg_chat_id}")
        text = "\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")],
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "admin_add_channel")
async def cb_add_channel(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    """Start adding a channel via FSM."""
    if not session or not await _check_admin(call.from_user.id, session, "manage_channels"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer("Kanal Telegram chat ID sini yuboring (masalan: -1001234567890):")
    await state.set_state(AddChannelSG.tg_chat_id)
    await call.answer()


# ─── Admin management ───────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_manage_admins")
async def cb_manage_admins(call: CallbackQuery, session: AsyncSession | None = None):
    """Show admin list."""
    if not session or not await _check_admin(call.from_user.id, session, "manage_admins"):
        return await call.answer("Ruxsat yo'q", show_alert=True)

    admin_repo = AdminRepository(session)
    admins = await admin_repo.get_all_admins()

    lines = ["👥 <b>Adminlar</b>\n"]
    for a in admins:
        lines.append(f"  • ID: <code>{a.user_id}</code> — {a.role}")

    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="admin_add_admin")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")],
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "admin_add_admin")
async def cb_add_admin_prompt(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    """Prompt for new admin user ID."""
    if not session or not await _check_admin(call.from_user.id, session, "manage_admins"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer(
        "Yangi admin user ID sini yuboring:\n"
        "(Rollar: owner, admin, content_mgr, broadcaster)\n\n"
        "Format: <code>USER_ID rol</code>\n"
        "Masalan: <code>123456789 admin</code>"
    )
    await state.set_state(AddAdminSG.user_input)
    await call.answer()


@router.message(AddAdminSG.user_input, F.text)
async def handle_admin_input(message: Message, state: FSMContext, session: AsyncSession | None = None):
    """Process admin add input."""
    if not session or not await _check_admin(message.from_user.id, session, "manage_admins"):
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
        await message.reply(f"Noto'g'ri rol. Mavjud rollar: {', '.join(valid_roles)}")
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
        await message.reply(f"✅ Yangi admin qo'shildi: {user_id} ({role})")

    await state.clear()


# ─── Start movie/series add from admin panel ─────────────────────────────
@router.callback_query(F.data == "admin_add_movie")
async def cb_add_movie(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    """Start adding a movie from admin panel."""
    if not session or not await _check_admin(call.from_user.id, session, "manage_content"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    from bot.states import AddMovieSG
    await call.message.answer("🎬 Kino nomini kiriting:")
    await state.set_state(AddMovieSG.title)
    await call.answer()


@router.callback_query(F.data == "admin_add_series")
async def cb_add_series(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    """Start adding a series from admin panel."""
    if not session or not await _check_admin(call.from_user.id, session, "manage_content"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    from bot.states import AddSeriesSG
    await call.message.answer("📺 Serial nomini kiriting:")
    await state.set_state(AddSeriesSG.title)
    await call.answer()


@router.callback_query(F.data == "admin_create_broadcast")
async def cb_create_broadcast(call: CallbackQuery, state: FSMContext, session: AsyncSession | None = None):
    """Start broadcast creation."""
    if not session or not await _check_admin(call.from_user.id, session, "broadcast"):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.message.answer("📢 Broadcast matnini yuboring (yoki media + caption):")
    await state.set_state(BroadcastSG.text)
    await call.answer()
