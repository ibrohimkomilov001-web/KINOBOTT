from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional

# ═══════════════════════════════════════════════════════════════
# Admin Reply Keyboard (asosiy panel)
# ═══════════════════════════════════════════════════════════════

ADMIN_BUTTONS = {
    "stats": "📊 Statistika",
    "broadcast": "📢 Xabar yuborish",
    "channels": "� Kanal boshqaruvi",
    "movies": "🎬 Kino boshqaruvi",
    "settings": "⚙️ Sozlamalar",
    "admins": "👥 Adminlar",
}


def admin_main_reply_kb() -> ReplyKeyboardMarkup:
    """Admin asosiy reply keyboard (2x3)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADMIN_BUTTONS["stats"]), KeyboardButton(text=ADMIN_BUTTONS["broadcast"])],
            [KeyboardButton(text=ADMIN_BUTTONS["channels"]), KeyboardButton(text=ADMIN_BUTTONS["movies"])],
            [KeyboardButton(text=ADMIN_BUTTONS["settings"]), KeyboardButton(text=ADMIN_BUTTONS["admins"])],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def remove_reply_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ═══════════════════════════════════════════════════════════════
# Kino boshqaruvi sub-menu
# ═══════════════════════════════════════════════════════════════

def movie_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="movie_add")],
        [InlineKeyboardButton(text="📺 Serial qo'shish", callback_data="series_add")],
        [InlineKeyboardButton(text="📋 Kinolar ro'yxati", callback_data="movie_list:0")],
        [InlineKeyboardButton(text="📋 Seriallar ro'yxati", callback_data="series_list:0")],
    ])


def movie_list_kb(movies: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Kino ro'yxati paginatsiya bilan."""
    builder = InlineKeyboardBuilder()
    for m in movies:
        builder.row(InlineKeyboardButton(
            text=f"🎬 {m.code} — {m.title}",
            callback_data=f"movie_view:{m.id}"
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"movie_list:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"movie_list:{page + 1}"))
    if nav:
        builder.row(*nav)
    return builder.as_markup()


def movie_detail_kb(movie_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"movie_edit:{movie_id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"movie_del:{movie_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="movie_list:0")],
    ])


# ═══════════════════════════════════════════════════════════════
# Serial sub-menu
# ═══════════════════════════════════════════════════════════════

def series_list_kb(series_list: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in series_list:
        builder.row(InlineKeyboardButton(
            text=f"📺 {s.code} — {s.title}",
            callback_data=f"series_view:{s.id}"
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"series_list:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"series_list:{page + 1}"))
    if nav:
        builder.row(*nav)
    return builder.as_markup()


def series_detail_kb(series_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Sezon qo'shish", callback_data=f"season_add:{series_id}")],
        [InlineKeyboardButton(text="➕ Epizod qo'shish", callback_data=f"episode_add:{series_id}")],
        [
            InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"series_edit:{series_id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"series_del:{series_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="series_list:0")],
    ])


def season_episodes_kb(episodes: list, series_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ep in episodes:
        title = ep.title or f"Epizod {ep.episode_number}"
        builder.row(InlineKeyboardButton(text=f"▶️ {ep.episode_number}. {title}", callback_data=f"ep_play:{ep.id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"series_view:{series_id}"))
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════
# Kanal boshqaruvi
# ═══════════════════════════════════════════════════════════════

def channels_kb(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        req = "✅" if ch.is_required else "❌"
        builder.row(InlineKeyboardButton(
            text=f"{req} {ch.title}",
            callback_data=f"ch_view:{ch.id}"
        ))
    builder.row(InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="ch_add"))
    return builder.as_markup()


def channel_detail_kb(ch) -> InlineKeyboardMarkup:
    req_text = "❌ Majburiy o'chirish" if ch.is_required else "✅ Majburiy yoqish"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=req_text, callback_data=f"ch_toggle:{ch.id}")],
        [InlineKeyboardButton(text="🔗 Invite link yangilash", callback_data=f"ch_invite:{ch.id}")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"ch_del:{ch.id}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ch_list")],
    ])


# ═══════════════════════════════════════════════════════════════
# Broadcast
# ═══════════════════════════════════════════════════════════════

def broadcast_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Yangi xabar", callback_data="bc_mode:custom")],
        [InlineKeyboardButton(text="↗️ Forward qilish", callback_data="bc_mode:forward")],
        [InlineKeyboardButton(text="📋 Copy qilish", callback_data="bc_mode:copy")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="bc_cancel")],
    ])


def broadcast_after_content_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Tugma qo'shish", callback_data="bc_add_buttons")],
        [InlineKeyboardButton(text="🎯 Segmentlash", callback_data="bc_segment")],
        [InlineKeyboardButton(text="👁 Ko'rik ko'rish", callback_data="bc_preview")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="bc_cancel")],
    ])


def broadcast_segment_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Barchaga", callback_data="bc_seg:all"),
        ],
        [
            InlineKeyboardButton(text="7 kun faol", callback_data="bc_seg:active_7"),
            InlineKeyboardButton(text="30 kun faol", callback_data="bc_seg:active_30"),
        ],
        [
            InlineKeyboardButton(text="⭐ Premium", callback_data="bc_seg:premium"),
        ],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="bc_back_content")],
    ])


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Yuborish", callback_data="bc_confirm"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="bc_cancel"),
        ],
    ])


def broadcast_controls(broadcast_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏸ Pauza", callback_data=f"bc_pause:{broadcast_id}"),
            InlineKeyboardButton(text="❌ Bekor", callback_data=f"bc_stop:{broadcast_id}"),
        ],
    ])


# ═══════════════════════════════════════════════════════════════
# Sozlamalar
# ═══════════════════════════════════════════════════════════════

def settings_kb(auto_code: bool, force_sub: bool, maintenance: bool) -> InlineKeyboardMarkup:
    ac = "🟢" if auto_code else "🔴"
    fs = "🟢" if force_sub else "🔴"
    mt = "🟢" if maintenance else "🔴"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{ac} Avtomatik kod", callback_data="set_toggle:auto_code"),
         InlineKeyboardButton(text=f"{fs} Majburiy obuna", callback_data="set_toggle:force_subscription")],
        [InlineKeyboardButton(text=f"{mt} Texnik ishlar", callback_data="set_toggle:maintenance_mode"),
         InlineKeyboardButton(text="📊 Broadcast tezligi", callback_data="set_bc_rate")],
        [InlineKeyboardButton(text="💾 Backup olish", callback_data="set_backup"),
         InlineKeyboardButton(text="📥 Backup tiklash", callback_data="set_restore")],
        [InlineKeyboardButton(text="📺 Baza kanal ID", callback_data="set_base_channel")],
    ])


# ═══════════════════════════════════════════════════════════════
# Adminlar
# ═══════════════════════════════════════════════════════════════

def admins_kb(admins: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for a in admins:
        builder.row(InlineKeyboardButton(
            text=f"👤 {a.user_id} — {a.role}",
            callback_data=f"adm_view:{a.user_id}"
        ))
    builder.row(InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="adm_add"))
    return builder.as_markup()


def admin_detail_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"adm_del:{user_id}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_list")],
    ])


# ═══════════════════════════════════════════════════════════════
# Umumiy
# ═══════════════════════════════════════════════════════════════

def confirm_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"{prefix}_confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{prefix}_cancel"),
        ]
    ])


def back_kb(callback_data: str = "admin_back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=callback_data)]
    ])


def skip_kb(callback_data: str = "skip") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏩ O'tkazish", callback_data=callback_data)]
    ])


def parse_buttons_text(text: str) -> Optional[InlineKeyboardMarkup]:
    """Parse admin button text into InlineKeyboardMarkup.
    Format: each line is a row, 'Text | url' or 'Text | callback:data'
    """
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return None
    builder = InlineKeyboardBuilder()
    for line in lines:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 2:
            btn_text, btn_data = parts
            if btn_data.startswith("http"):
                builder.row(InlineKeyboardButton(text=btn_text, url=btn_data))
            elif btn_data.startswith("callback:"):
                builder.row(InlineKeyboardButton(text=btn_text, callback_data=btn_data.replace("callback:", "")))
            else:
                builder.row(InlineKeyboardButton(text=btn_text, url=btn_data))
        elif len(parts) == 1:
            builder.row(InlineKeyboardButton(text=parts[0], url="https://t.me"))
    return builder.as_markup()
