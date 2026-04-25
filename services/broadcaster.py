"""Broadcast service with rate limiting."""

import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.user_repo import UserRepository
from db.repositories.broadcast_repo import BroadcastRepository
from db import models
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BroadcastEngine:
    """Rate-limited broadcast engine with worker pool."""

    def __init__(self, session: AsyncSession, bot: Bot, bot_rate: float = 28, userbot_rate: float = 20):
        self.session = session
        self.bot = bot
        self.bot_rate = bot_rate  # messages/second via bot API
        self.userbot_rate = userbot_rate  # messages/second via userbot
        self.broadcast_repo = BroadcastRepository(session)
        self.user_repo = UserRepository(session)

    async def start(self, broadcast_id: int, admin_chat_id: int, worker_count: int = 3) -> bool:
        """Start a broadcast with worker pool."""
        broadcast = await self.broadcast_repo.get_by_id(broadcast_id)
        if not broadcast:
            logger.error(f"Broadcast {broadcast_id} not found")
            return False

        # Get target users
        users = await self.user_repo.get_users_for_broadcast(
            segment=broadcast.segment,
            limit=10000
        )
        logger.info(f"Starting broadcast {broadcast_id} for {len(users)} users")

        # Start broadcast in DB
        await self.broadcast_repo.start_broadcast(broadcast_id, len(users))
        await self.session.commit()

        # Create tasks for workers
        queue: asyncio.Queue = asyncio.Queue()
        for user_id in users:
            await queue.put(user_id)

        # Add sentinel values to stop workers
        for _ in range(worker_count):
            await queue.put(None)

        # Run workers
        workers = [
            asyncio.create_task(self._worker(broadcast_id, broadcast, queue))
            for _ in range(worker_count)
        ]

        # Wait for all workers to complete
        await asyncio.gather(*workers)

        # Complete broadcast
        broadcast = await self.broadcast_repo.get_by_id(broadcast_id)
        await self.broadcast_repo.complete_broadcast(broadcast_id)
        await self.session.commit()

        # Notify admin
        try:
            await self.bot.send_message(
                admin_chat_id,
                f"✅ Broadcast #{broadcast_id} tugallandi!\n"
                f"Yuborildi: {broadcast.sent_count}\n"
                f"Xatolik: {broadcast.failed_count}\n"
                f"Bloklangan: {broadcast.blocked_count}",
            )
        except Exception:
            pass

        logger.info(
            f"Broadcast {broadcast_id} completed. "
            f"Sent: {broadcast.sent_count}, Failed: {broadcast.failed_count}, Blocked: {broadcast.blocked_count}"
        )
        return True

    async def _worker(self, broadcast_id: int, broadcast: models.Broadcast, queue: asyncio.Queue):
        """Worker task that sends messages."""
        rate_limit = 1.0 / self.bot_rate

        while True:
            user_id = await queue.get()
            if user_id is None:
                break  # Sentinel received, stop worker

            try:
                success = await self._send_message(broadcast, user_id)
                if success:
                    await self.broadcast_repo.increment_sent(broadcast_id)
                else:
                    await self.broadcast_repo.increment_failed(broadcast_id)
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                await self.broadcast_repo.increment_failed(broadcast_id)
            finally:
                await asyncio.sleep(rate_limit)

    async def _send_message(self, broadcast: models.Broadcast, user_id: int) -> bool:
        """Send broadcast message to user."""
        try:
            if broadcast.mode == "copy":
                # Copy from base channel (not implemented yet)
                pass
            elif broadcast.mode == "forward":
                # Forward via userbot (not implemented yet)
                pass
            else:  # custom
                # Send custom message
                text = broadcast.text or ""

                # Send based on media type
                if broadcast.media_video:
                    await self.bot.send_video(user_id, broadcast.media_video, caption=text)
                elif broadcast.media_photo:
                    await self.bot.send_photo(user_id, broadcast.media_photo, caption=text)
                elif broadcast.media_document:
                    await self.bot.send_document(user_id, broadcast.media_document, caption=text)
                else:
                    await self.bot.send_message(user_id, text)

            return True

        except TelegramBadRequest as e:
            if "bot was blocked" in str(e).lower():
                await self.user_repo.mark_blocked(user_id)
                await self.session.commit()
            logger.warning(f"Bad request to {user_id}: {e}")
            return False
        except TelegramAPIError as e:
            logger.warning(f"API error to {user_id}: {e}")
            return False

    async def pause(self, broadcast_id: int) -> bool:
        """Pause a broadcast."""
        await self.broadcast_repo.pause_broadcast(broadcast_id)
        await self.session.commit()
        return True

    async def resume(self, broadcast_id: int) -> bool:
        """Resume a paused broadcast."""
        await self.broadcast_repo.resume_broadcast(broadcast_id)
        await self.session.commit()
        return True

    async def cancel(self, broadcast_id: int) -> bool:
        """Cancel a broadcast."""
        await self.broadcast_repo.fail_broadcast(broadcast_id)
        await self.session.commit()
        return True
