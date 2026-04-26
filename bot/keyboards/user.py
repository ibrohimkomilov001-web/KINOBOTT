from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def rating_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    """Return inline keyboard for rating 1-5 + comment."""
    stars = [InlineKeyboardButton(text=f"{'⭐' * i}", callback_data=f"rate:{movie_id}:{i}") for i in range(1, 6)]
    return InlineKeyboardMarkup(inline_keyboard=[
        stars,
        [InlineKeyboardButton(text="💬 Komment yozish", callback_data=f"comment:movie:{movie_id}")],
    ])


def simple_menu() -> InlineKeyboardMarkup:
    """Main user menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔝 Top kinolar", callback_data="top_movies")],
        [InlineKeyboardButton(text="🎲 Tasodifiy", callback_data="random")],
        [InlineKeyboardButton(text="🔗 Referral", callback_data="my_referral")],
    ])


def series_rating_keyboard(series_id: int) -> InlineKeyboardMarkup:
    """Return inline keyboard for rating a series 1-5 + comment."""
    stars = [InlineKeyboardButton(text=f"{'⭐' * i}", callback_data=f"rate_s:{series_id}:{i}") for i in range(1, 6)]
    return InlineKeyboardMarkup(inline_keyboard=[
        stars,
        [InlineKeyboardButton(text="💬 Komment yozish", callback_data=f"comment:series:{series_id}")],
    ])


def referral_keyboard(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    """Referral link sharing button."""
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Ulashish", url=f"https://t.me/share/url?url={link}&text=Kinobotni sinab ko'ring!")],
    ])


def subscription_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Subscription check keyboard with channel links."""
    builder = InlineKeyboardBuilder()
    for ch in channels:
        link = ch.invite_link or f"https://t.me/{ch.title}"
        builder.row(InlineKeyboardButton(text=f"📢 {ch.title}", url=link))
    builder.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription"))
    return builder.as_markup()
