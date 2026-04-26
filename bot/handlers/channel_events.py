"""Channel/group event handlers (join requests, member updates)."""

from aiogram import Router, F
from aiogram.types import ChatJoinRequest
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.channel_repo import ChannelRepository
from db.repositories.user_repo import UserRepository
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.chat_join_request()
async def handle_join_request(event: ChatJoinRequest, session: AsyncSession | None = None):
    """Auto-approve join requests for `request_join` channels."""
    if not session:
        return

    chat_id = event.chat.id
    user_id = event.from_user.id

    repo = ChannelRepository(session)
    ch = await repo.get_by_tg_chat_id(chat_id)

    if not ch:
        logger.info(f"chat_join_request from unknown channel {chat_id}, ignoring")
        return

    if ch.type != "request_join":
        logger.info(f"chat_join_request for non-request channel {chat_id}, ignoring")
        return

    try:
        # 1) Approve
        await event.approve()
        logger.info(f"Approved join request: user={user_id}, channel={chat_id}")

        # 2) Mark in DB
        existing = await repo.get_join_request(user_id, ch.id)
        if not existing:
            await repo.add_join_request(user_id, ch.id)
        await repo.approve_join_request(user_id, ch.id)

        # 3) Track referral if user came via bot referrer
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)
        if user and not await _has_referral(session, user_id, ch.id):
            await repo.add_referral(user_id, ch.id)

        await session.commit()

        # 4) Welcome the user back to the bot
        try:
            from bot.loader import bot
            await bot.send_message(
                user_id,
                f"✅ <b>{ch.title}</b> ga obunangiz tasdiqlandi!\n\n"
                f"Botga qaytishingiz mumkin: /start"
            )
        except Exception as e:
            logger.debug(f"Could not message user {user_id}: {e}")

    except Exception as e:
        logger.error(f"Error approving join request: {e}")
        try:
            await session.rollback()
        except Exception:
            pass


async def _has_referral(session: AsyncSession, user_id: int, channel_id: int) -> bool:
    """Check if referral already recorded."""
    from sqlalchemy import select
    from db import models
    stmt = select(models.ChannelReferral).where(
        models.ChannelReferral.user_id == user_id,
        models.ChannelReferral.channel_id == channel_id
    )
    result = await session.execute(stmt)
    return result.scalars().first() is not None
