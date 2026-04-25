from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def broadcast_controls(broadcast_id: int) -> InlineKeyboardMarkup:
    """Broadcast control buttons."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Boshlash", callback_data=f"bc_start:{broadcast_id}")],
        [
            InlineKeyboardButton(text="⏸ To'xtatish", callback_data=f"bc_pause:{broadcast_id}"),
            InlineKeyboardButton(text="▶ Davom", callback_data=f"bc_resume:{broadcast_id}"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"bc_cancel:{broadcast_id}")],
    ])


def admin_main_kb() -> InlineKeyboardMarkup:
    """Admin main panel keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Kino qo'shish", callback_data="admin_add_movie")],
        [InlineKeyboardButton(text="📺 Serial qo'shish", callback_data="admin_add_series")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_create_broadcast")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📋 Kanallar", callback_data="admin_channels")],
        [InlineKeyboardButton(text="👥 Adminlar", callback_data="admin_manage_admins")],
    ])


def confirm_kb(prefix: str) -> InlineKeyboardMarkup:
    """Generic confirm/cancel keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"{prefix}_confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{prefix}_cancel"),
        ]
    ])
