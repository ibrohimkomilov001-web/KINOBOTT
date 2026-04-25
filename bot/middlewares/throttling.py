from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Update, Message
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Store last message time per user
_user_last_action: dict[int, datetime] = {}
_last_cleanup = datetime.now()
_CLEANUP_INTERVAL = timedelta(minutes=10)
_MAX_ENTRIES = 10000


class ThrottlingMiddleware(BaseMiddleware):
    """Middleware that limits user action rate."""

    delay = 1.0

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        """Check throttle limit."""
        global _last_cleanup

        user = None
        if event.message:
            user = event.message.from_user
        elif event.callback_query:
            user = event.callback_query.from_user

        if not user:
            return await handler(event, data)

        user_id = user.id
        now = datetime.now()

        # Periodic cleanup of stale entries
        if now - _last_cleanup > _CLEANUP_INTERVAL or len(_user_last_action) > _MAX_ENTRIES:
            cutoff = now - timedelta(minutes=5)
            stale = [uid for uid, ts in _user_last_action.items() if ts < cutoff]
            for uid in stale:
                del _user_last_action[uid]
            _last_cleanup = now

        if user_id in _user_last_action:
            last_action = _user_last_action[user_id]
            if now - last_action < timedelta(seconds=self.delay):
                logger.debug(f"Throttling user {user_id}")
                return

        _user_last_action[user_id] = now
        return await handler(event, data)
