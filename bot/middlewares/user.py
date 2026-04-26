from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, Update
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories import UserRepository
import logging

logger = logging.getLogger(__name__)


class UserTrackingMiddleware(BaseMiddleware):
    """Middleware that tracks user activity."""

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        """Track user activity."""
        session: AsyncSession = data.get("session")
        
        # Get user from event
        user = None
        if event.message:
            user = event.message.from_user
        elif event.callback_query:
            user = event.callback_query.from_user
        
        if user and session:
            try:
                user_repo = UserRepository(session)
                
                # Get or create user
                db_user = await user_repo.get_or_create(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    lang=user.language_code or "uz"
                )
                
                # Update premium status if available
                if hasattr(user, 'is_premium'):
                    db_user.is_premium = bool(user.is_premium)
                
                # Update last_active_at
                await user_repo.update_last_active(user.id)
                
                # Commit changes
                await session.commit()
                
                # Store in context
                data["user"] = db_user
                
            except Exception as e:
                logger.error(f"Error tracking user {user.id}: {e}")
                await session.rollback()
        
        return await handler(event, data)
