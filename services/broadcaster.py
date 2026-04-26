"""Broadcast service with rate limiting, real-time progress, owns its DB sessions."""

import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db.base import AsyncSessionLocal
from db.repositories.user_repo import UserRepository
from db.repositories.broadcast_repo import BroadcastRepository
from db.constants import BroadcastStatus
from db import models
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BroadcastEngine:
    """Rate-limited broadcast engine. Owns its DB sessions (no shared session)."""

    def __init__(self, bot: Bot, bot_rate: float = 28):
        self.bot = bot
        self.bot_rate = bot_rate
        self._cancelled = False

    def _build_keyboard(self, buttons_data) -> Optional[InlineKeyboardMarkup]:
        """Build InlineKeyboardMarkup from JSON button data.

        Supports two formats:
        1. List of rows: [[{text, url}, {text, url}], [{text, url}]]
        2. Flat list (legacy): [{text, url}, {text, url}]
        """
        if not buttons_data:
            return None
        builder = InlineKeyboardBuilder()

        if isinstance(buttons_data, list) and buttons_data and isinstance(buttons_data[0], list):
            # New format: list of rows
            for row in buttons_data:
                row_buttons = []
                for btn in row:
                    if not isinstance(btn, dict):
                        continue
                    if btn.get("url"):
                        row_buttons.append(InlineKeyboardButton(text=btn.get("text", ""), url=btn["url"]))
                    elif btn.get("callback_data"):
                        row_buttons.append(InlineKeyboardButton(text=btn.get("text", ""), callback_data=btn["callback_data"]))
                if row_buttons:
                    builder.row(*row_buttons)
        else:
            # Legacy: flat list, 1 button per row
            for btn in buttons_data:
                if not isinstance(btn, dict):
                    continue
                if btn.get("url"):
                    builder.row(InlineKeyboardButton(text=btn.get("text", ""), url=btn["url"]))
                elif btn.get("callback_data"):
                    builder.row(InlineKeyboardButton(text=btn.get("text", ""), callback_data=btn["callback_data"]))

        return builder.as_markup() if buttons_data else None

    async def start(self, broadcast_id: int, admin_chat_id: int,
                    worker_count: int = 3,
                    progress_chat_id: Optional[int] = None,
                    progress_message_id: Optional[int] = None) -> bool:
        """Start a broadcast. Opens its OWN DB sessions for safety."""
        # 1) Load broadcast snapshot in a one-shot session
        async with AsyncSessionLocal() as init_session:
            repo = BroadcastRepository(init_session)
            broadcast = await repo.get_by_id(broadcast_id)
            if not broadcast:
                logger.error(f"Broadcast {broadcast_id} not found")
                return False

            # Snapshot all data we'll need for sending (so we don't hit the DB during send loop)
            bc_snapshot = {
                "id": broadcast.id,
                "text": broadcast.text or "",
                "media_photo": broadcast.media_photo,
                "media_video": broadcast.media_video,
                "media_animation": broadcast.media_animation,
                "media_audio": broadcast.media_audio,
                "media_voice": broadcast.media_voice,
                "media_document": broadcast.media_document,
                "buttons": broadcast.buttons,
                "segment": broadcast.segment or {},
                "mode": broadcast.mode,
            }

            user_repo = UserRepository(init_session)
            users = await user_repo.get_users_for_broadcast(segment=bc_snapshot["segment"], limit=100000)
            target_count = len(users)

            await repo.start_broadcast(broadcast_id, target_count)
            await init_session.commit()

        logger.info(
            f"Broadcast {broadcast_id}: {target_count} targets, "
            f"segment={bc_snapshot['segment'].get('type', 'all')}"
        )

        # 2) Worker queue
        queue: asyncio.Queue = asyncio.Queue()
        for uid in users:
            await queue.put(uid)
        for _ in range(worker_count):
            await queue.put(None)  # Sentinel for each worker

        # 3) Start progress updater (every 5s, OWN session)
        progress_task = None
        if progress_chat_id and progress_message_id:
            progress_task = asyncio.create_task(
                self._progress_updater(broadcast_id, progress_chat_id, progress_message_id)
            )

        # 4) Spawn workers (each with OWN session)
        workers = [
            asyncio.create_task(self._worker(broadcast_id, bc_snapshot, queue))
            for _ in range(worker_count)
        ]
        await asyncio.gather(*workers, return_exceptions=True)

        # 5) Stop progress updater
        if progress_task:
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

        # 6) Finalize and report
        async with AsyncSessionLocal() as final_session:
            repo = BroadcastRepository(final_session)
            broadcast = await repo.get_by_id(broadcast_id)
            if broadcast and broadcast.status != BroadcastStatus.FAILED.value:
                await repo.complete_broadcast(broadcast_id)
            await final_session.commit()
            broadcast = await repo.get_by_id(broadcast_id)

        # Final progress message
        if progress_chat_id and progress_message_id and broadcast:
            try:
                await self.bot.edit_message_text(
                    chat_id=progress_chat_id,
                    message_id=progress_message_id,
                    text=(
                        f"✅ <b>Broadcast #{broadcast_id} tugallandi</b>\n\n"
                        f"📤 Yuborildi: <b>{broadcast.sent_count}</b>\n"
                        f"❌ Xatolik: {broadcast.failed_count}\n"
                        f"🚫 Bloklangan: {broadcast.blocked_count}\n"
                        f"🎯 Maqsad: {broadcast.target_count}"
                    )
                )
            except Exception:
                pass

        # Notify admin
        if broadcast:
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

    async def _progress_updater(self, broadcast_id: int, chat_id: int, message_id: int):
        """Periodically update progress message every 5 seconds (OWN session per tick)."""
        from bot.keyboards.admin import broadcast_controls
        try:
            while True:
                await asyncio.sleep(5)
                try:
                    async with AsyncSessionLocal() as session:
                        repo = BroadcastRepository(session)
                        bc = await repo.get_by_id(broadcast_id)
                    if not bc or bc.status in (BroadcastStatus.COMPLETED.value, BroadcastStatus.FAILED.value):
                        break
                    pct = (bc.sent_count + bc.failed_count) * 100 // max(bc.target_count, 1)
                    text = (
                        f"🚀 <b>Broadcast #{broadcast_id}</b> ({bc.status})\n\n"
                        f"📤 Yuborildi: <b>{bc.sent_count}</b> / {bc.target_count} ({pct}%)\n"
                        f"❌ Xato: {bc.failed_count}\n"
                        f"🚫 Block: {bc.blocked_count}"
                    )
                    await self.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=text,
                        reply_markup=broadcast_controls(broadcast_id)
                    )
                except TelegramBadRequest:
                    pass  # Message not modified
                except Exception as e:
                    logger.debug(f"progress update: {e}")
        except asyncio.CancelledError:
            raise

    async def _worker(self, broadcast_id: int, bc_snapshot: dict, queue: asyncio.Queue):
        """Worker — rate limited message sender. OWN session per worker."""
        rate_limit = 1.0 / self.bot_rate

        async with AsyncSessionLocal() as session:
            repo = BroadcastRepository(session)
            user_repo = UserRepository(session)

            while True:
                if self._cancelled:
                    break

                user_id = await queue.get()
                if user_id is None:
                    break

                # Check pause/cancel state
                bc = await repo.get_by_id(broadcast_id)
                if bc and bc.status == BroadcastStatus.PAUSED.value:
                    while True:
                        await asyncio.sleep(2)
                        bc = await repo.get_by_id(broadcast_id)
                        if not bc or bc.status != BroadcastStatus.PAUSED.value:
                            break
                    if not bc or bc.status == BroadcastStatus.FAILED.value:
                        break

                if bc and bc.status == BroadcastStatus.FAILED.value:
                    break

                try:
                    ok = await self._send_message(bc_snapshot, user_id, user_repo)
                    if ok:
                        await repo.increment_sent(broadcast_id)
                    else:
                        await repo.increment_failed(broadcast_id)
                    await session.commit()
                except Exception as e:
                    logger.error(f"Broadcast worker error for {user_id}: {e}")
                    try:
                        await repo.increment_failed(broadcast_id)
                        await session.commit()
                    except Exception:
                        await session.rollback()
                finally:
                    await asyncio.sleep(rate_limit)

    async def _send_message(self, bc: dict, user_id: int, user_repo: UserRepository) -> bool:
        """Send broadcast message to one user. bc is a snapshot dict (not ORM object)."""
        try:
            kb = self._build_keyboard(bc.get("buttons"))
            text = bc.get("text", "") or ""

            if bc.get("media_video"):
                await self.bot.send_video(user_id, bc["media_video"], caption=text, reply_markup=kb)
            elif bc.get("media_photo"):
                await self.bot.send_photo(user_id, bc["media_photo"], caption=text, reply_markup=kb)
            elif bc.get("media_animation"):
                await self.bot.send_animation(user_id, bc["media_animation"], caption=text, reply_markup=kb)
            elif bc.get("media_audio"):
                await self.bot.send_audio(user_id, bc["media_audio"], caption=text, reply_markup=kb)
            elif bc.get("media_voice"):
                await self.bot.send_voice(user_id, bc["media_voice"], caption=text, reply_markup=kb)
            elif bc.get("media_document"):
                await self.bot.send_document(user_id, bc["media_document"], caption=text, reply_markup=kb)
            elif text:
                await self.bot.send_message(user_id, text, reply_markup=kb)
            else:
                return False
            return True

        except TelegramForbiddenError:
            try:
                await user_repo.mark_blocked(user_id)
            except Exception:
                pass
            return False
        except TelegramBadRequest as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err or "user is deactivated" in err:
                try:
                    await user_repo.mark_blocked(user_id)
                except Exception:
                    pass
            logger.warning(f"Bad request to {user_id}: {e}")
            return False
        except TelegramAPIError as e:
            if "flood" in str(e).lower():
                import re
                match = re.search(r"(\d+)", str(e))
                wait = int(match.group(1)) if match else 5
                logger.warning(f"Flood control: waiting {wait}s")
                await asyncio.sleep(wait)
                return False
            logger.warning(f"API error to {user_id}: {e}")
            return False

    async def cancel(self):
        """Mark engine as cancelled — workers will stop on next iteration."""
        self._cancelled = True
