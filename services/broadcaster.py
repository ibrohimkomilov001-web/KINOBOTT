"""Broadcast service with rate limiting and maximum API usage."""

import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.user_repo import UserRepository
from db.repositories.broadcast_repo import BroadcastRepository
from db.constants import BroadcastStatus
from db import models
from datetime import datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class BroadcastEngine:
    """Rate-limited broadcast engine with worker pool — Maximum API."""

    def __init__(self, session: AsyncSession, bot: Bot, bot_rate: float = 28):
        self.session = session
        self.bot = bot
        self.bot_rate = bot_rate
        self.broadcast_repo = BroadcastRepository(session)
        self.user_repo = UserRepository(session)
        self._cancelled = False

    def _build_keyboard(self, buttons_data) -> Optional[InlineKeyboardMarkup]:
        """Build InlineKeyboardMarkup from JSON button data."""
        if not buttons_data:
            return None
        builder = InlineKeyboardBuilder()
        for btn in buttons_data:
            if isinstance(btn, dict):
                text = btn.get("text", "")
                url = btn.get("url")
                cb = btn.get("callback_data")
                if url:
                    builder.row(InlineKeyboardButton(text=text, url=url))
                elif cb:
                    builder.row(InlineKeyboardButton(text=text, callback_data=cb))
        return builder.as_markup() if buttons_data else None

    async def start(self, broadcast_id: int, admin_chat_id: int, worker_count: int = 3) -> bool:
        """Start a broadcast with worker pool."""
        broadcast = await self.broadcast_repo.get_by_id(broadcast_id)
        if not broadcast:
            logger.error(f"Broadcast {broadcast_id} not found")
            return False

        # Get target users based on segment
        segment = broadcast.segment or {}
        seg_type = segment.get("type", "all") if isinstance(segment, dict) else "all"
        users = await self.user_repo.get_users_for_broadcast(segment=segment, limit=100000)
        logger.info(f"Broadcast {broadcast_id}: {len(users)} targets, segment={seg_type}")

        await self.broadcast_repo.start_broadcast(broadcast_id, len(users))
        await self.session.commit()

        # Worker queue
        queue: asyncio.Queue = asyncio.Queue()
        for uid in users:
            await queue.put(uid)
        for _ in range(worker_count):
            await queue.put(None)

        workers = [
            asyncio.create_task(self._worker(broadcast_id, broadcast, queue))
            for _ in range(worker_count)
        ]
        await asyncio.gather(*workers)

        # Finalize
        broadcast = await self.broadcast_repo.get_by_id(broadcast_id)
        if broadcast.status != BroadcastStatus.FAILED.value:
            await self.broadcast_repo.complete_broadcast(broadcast_id)
        await self.session.commit()

        # Report to admin
        try:
            await self.bot.send_message(
                admin_chat_id,
                f"✅ <b>Broadcast #{broadcast_id} tugallandi!</b>\n\n"
                f"📤 Yuborildi: {broadcast.sent_count}\n"
                f"❌ Xatolik: {broadcast.failed_count}\n"
                f"🚫 Bloklangan: {broadcast.blocked_count}\n"
                f"🎯 Jami maqsad: {broadcast.target_count}",
            )
        except Exception:
            pass

        logger.info(
            f"Broadcast {broadcast_id} done: sent={broadcast.sent_count}, "
            f"fail={broadcast.failed_count}, blocked={broadcast.blocked_count}"
        )
        return True

    async def _worker(self, broadcast_id: int, broadcast: models.Broadcast, queue: asyncio.Queue):
        """Worker — rate limited message sender."""
        rate_limit = 1.0 / self.bot_rate

        while True:
            if self._cancelled:
                break

            user_id = await queue.get()
            if user_id is None:
                break

            # Check if broadcast paused/cancelled
            bc = await self.broadcast_repo.get_by_id(broadcast_id)
            if bc and bc.status == BroadcastStatus.PAUSED.value:
                # Wait until resumed or cancelled
                while True:
                    await asyncio.sleep(2)
                    bc = await self.broadcast_repo.get_by_id(broadcast_id)
                    if not bc or bc.status != BroadcastStatus.PAUSED.value:
                        break
                if not bc or bc.status == BroadcastStatus.FAILED.value:
                    break

            if bc and bc.status == BroadcastStatus.FAILED.value:
                break

            try:
                ok = await self._send_message(broadcast, user_id)
                if ok:
                    await self.broadcast_repo.increment_sent(broadcast_id)
                else:
                    await self.broadcast_repo.increment_failed(broadcast_id)
            except Exception as e:
                logger.error(f"Broadcast worker error for {user_id}: {e}")
                await self.broadcast_repo.increment_failed(broadcast_id)
            finally:
                await asyncio.sleep(rate_limit)

    async def _send_message(self, broadcast: models.Broadcast, user_id: int) -> bool:
        """Send message to one user — supports all modes and inline buttons."""
        try:
            kb = self._build_keyboard(broadcast.buttons)
            text = broadcast.text or ""

            if broadcast.mode == "forward":
                # Forward requires source chat_id + message_id stored in text as JSON
                # For now fallback to copy behavior
                return await self._send_custom(user_id, text, broadcast, kb)
            elif broadcast.mode == "copy":
                return await self._send_custom(user_id, text, broadcast, kb)
            else:
                return await self._send_custom(user_id, text, broadcast, kb)

        except TelegramForbiddenError:
            await self.user_repo.mark_blocked(user_id)
            await self.session.commit()
            return False
        except TelegramBadRequest as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err:
                await self.user_repo.mark_blocked(user_id)
                await self.session.commit()
            logger.warning(f"Bad request to {user_id}: {e}")
            return False
        except TelegramAPIError as e:
            if "flood" in str(e).lower():
                # Respect flood wait
                import re
                match = re.search(r"(\d+)", str(e))
                wait = int(match.group(1)) if match else 5
                logger.warning(f"Flood control: waiting {wait}s")
                await asyncio.sleep(wait)
                return False
            logger.warning(f"API error to {user_id}: {e}")
            return False

    async def _send_custom(self, user_id: int, text: str, bc: models.Broadcast,
                           kb: Optional[InlineKeyboardMarkup]) -> bool:
        """Send custom broadcast message with media + buttons."""
        if bc.media_video:
            await self.bot.send_video(user_id, bc.media_video, caption=text, reply_markup=kb)
        elif bc.media_photo:
            await self.bot.send_photo(user_id, bc.media_photo, caption=text, reply_markup=kb)
        elif bc.media_animation:
            await self.bot.send_animation(user_id, bc.media_animation, caption=text, reply_markup=kb)
        elif bc.media_audio:
            await self.bot.send_audio(user_id, bc.media_audio, caption=text, reply_markup=kb)
        elif bc.media_document:
            await self.bot.send_document(user_id, bc.media_document, caption=text, reply_markup=kb)
        elif text:
            await self.bot.send_message(user_id, text, reply_markup=kb)
        else:
            return False
        return True

    async def pause(self, broadcast_id: int) -> bool:
        await self.broadcast_repo.pause_broadcast(broadcast_id)
        await self.session.commit()
        return True

    async def resume(self, broadcast_id: int) -> bool:
        await self.broadcast_repo.resume_broadcast(broadcast_id)
        await self.session.commit()
        return True

    async def cancel(self, broadcast_id: int) -> bool:
        self._cancelled = True
        await self.broadcast_repo.fail_broadcast(broadcast_id)
        await self.session.commit()
        return True
