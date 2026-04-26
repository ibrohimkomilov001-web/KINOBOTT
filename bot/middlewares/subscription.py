from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, Update, CallbackQuery
from aiogram.enums import ChatMemberStatus
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories import ChannelRepository, SettingsRepository
from db.constants import SettingKey
from bot.keyboards.user import subscription_keyboard
import logging

logger = logging.getLogger(__name__)

# Statuses considered "subscribed"
OK_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


class SubscriptionMiddleware(BaseMiddleware):
    """Middleware that checks force subscription."""

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        """Check if user is subscribed to required channels."""
        session: AsyncSession = data.get("session")

        # Get user and message/callback from event
        tg_user = None
        target = None  # message or callback_query for sending response
        if event.message:
            tg_user = event.message.from_user
            target = event.message
        elif event.callback_query:
            tg_user = event.callback_query.from_user
            target = event.callback_query

        # chat_join_request, chat_member, my_chat_member, inline_query — bypass subscription check
        if not target:
            return await handler(event, data)

        if not tg_user or not session:
            return await handler(event, data)

        # Allow /start through always (user needs to start the bot)
        if event.message and event.message.text and event.message.text.startswith("/start"):
            return await handler(event, data)

        # Allow subscription check callback through
        if event.callback_query and event.callback_query.data == "check_subscription":
            return await handler(event, data)

        try:
            settings_repo = SettingsRepository(session)
            force_sub = await settings_repo.get_bool(SettingKey.FORCE_SUBSCRIPTION.value, True)

            if not force_sub:
                return await handler(event, data)

            channel_repo = ChannelRepository(session)
            required_channels = await channel_repo.get_required_channels()

            if not required_channels:
                return await handler(event, data)

            # Check subscription for each required channel
            from bot.loader import bot

            not_subscribed = []
            for channel in required_channels:
                is_member = False
                try:
                    member = await bot.get_chat_member(channel.tg_chat_id, tg_user.id)
                    if member.status in OK_STATUSES:
                        is_member = True
                except Exception as e:
                    logger.warning(f"Error checking sub for {tg_user.id} in {channel.tg_chat_id}: {e}")

                # For request_join channels: a recorded pending join_request also counts as subscribed
                if not is_member and channel.type == "request_join":
                    try:
                        req = await channel_repo.get_join_request(tg_user.id, channel.id)
                        if req is not None:
                            is_member = True
                    except Exception as e:
                        logger.debug(f"join_request lookup error: {e}")

                if not is_member:
                    not_subscribed.append(channel)

            if not_subscribed:
                text = "📢 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:"
                kb = subscription_keyboard(not_subscribed)
                if isinstance(target, CallbackQuery):
                    await target.answer("Avval kanallarga obuna bo'ling!", show_alert=True)
                    await target.message.answer(text, reply_markup=kb)
                else:
                    await target.answer(text, reply_markup=kb)
                return  # Block handler execution

        except Exception as e:
            logger.error(f"Subscription middleware error: {e}")
            # On error, allow through
        
        return await handler(event, data)
