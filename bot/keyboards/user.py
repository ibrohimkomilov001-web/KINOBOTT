from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def rating_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    """Return inline keyboard for rating 1-5."""
    buttons = [InlineKeyboardButton(text=f"{'⭐' * i}", callback_data=f"rate:{movie_id}:{i}") for i in range(1, 6)]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def simple_menu() -> InlineKeyboardMarkup:
    """Main user menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔝 Top kinolar", callback_data="top_movies")],
        [InlineKeyboardButton(text="🎲 Tasodifiy", callback_data="random")],
    ])


def subscription_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Subscription check keyboard with channel links."""
    builder = InlineKeyboardBuilder()
    for ch in channels:
        link = ch.invite_link or f"https://t.me/{ch.title}"
        builder.row(InlineKeyboardButton(text=f"📢 {ch.title}", url=link))
    builder.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription"))
    return builder.as_markup()
