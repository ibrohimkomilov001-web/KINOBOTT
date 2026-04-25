import asyncio
import logging
from config import settings
from utils.logging import setup_logging
from db.init_db import setup_database
from db.base import AsyncSessionLocal
from db.repositories.admin_repo import AdminRepository
from db.repositories.user_repo import UserRepository
from db.constants import AdminRole
from bot.loader import setup_dispatcher, bot
from bot.middlewares.db import DBMiddleware
from bot.middlewares.user import UserTrackingMiddleware
from bot.middlewares.subscription import SubscriptionMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware

from bot.handlers import admin as admin_handlers
from bot.handlers import user_callbacks
from bot.handlers import fsm_handlers
from bot.handlers import user as user_handlers

logger = setup_logging()


async def register_super_admins():
    """Register SUPER_ADMIN_IDS as owner admins in DB."""
    async with AsyncSessionLocal() as session:
        admin_repo = AdminRepository(session)
        user_repo = UserRepository(session)
        for admin_id in settings.SUPER_ADMIN_IDS:
            # Ensure user exists
            await user_repo.get_or_create(user_id=admin_id, first_name="Admin")
            # Ensure admin record exists
            existing = await admin_repo.get_by_user_id(admin_id)
            if not existing:
                await admin_repo.create(admin_id, role=AdminRole.OWNER.value)
                logger.info(f"✓ Registered super admin: {admin_id}")
        await session.commit()


async def main():
    logger.info("Starting KINOBOT")

    # Init DB
    await setup_database()

    # Register super admins
    await register_super_admins()

    # Setup dispatcher
    dp = await setup_dispatcher()

    # Register middlewares (order matters: DB first, then user tracking, then subscription, then throttle)
    dp.update.middleware(DBMiddleware())
    dp.update.middleware(UserTrackingMiddleware())
    dp.update.middleware(SubscriptionMiddleware())
    dp.update.middleware(ThrottlingMiddleware())

    # Include routers (order matters: admin/fsm first, then specific, then catch-all user last)
    dp.include_router(admin_handlers.router)
    dp.include_router(fsm_handlers.router)
    dp.include_router(user_callbacks.router)
    dp.include_router(user_handlers.router)

    # Start scheduler
    scheduler = None
    try:
        from services.scheduler import SchedulerService
        scheduler = SchedulerService(bot)
        await scheduler.start()
    except Exception as e:
        logger.warning(f"Scheduler failed to start: {e}")

    # Start polling
    try:
        logger.info("Starting polling...")
        await dp.start_polling(bot)
    finally:
        if scheduler:
            await scheduler.stop()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
