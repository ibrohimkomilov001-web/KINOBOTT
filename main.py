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
from bot.handlers import inline as inline_handlers

logger = setup_logging()


async def register_super_admins():
    """Register SUPER_ADMIN_IDS as owner admins in DB."""
    logger.info(f"Registering super admins: {settings.SUPER_ADMIN_IDS}")
    async with AsyncSessionLocal() as session:
        admin_repo = AdminRepository(session)
        user_repo = UserRepository(session)
        for admin_id in settings.SUPER_ADMIN_IDS:
            try:
                # Ensure user exists
                user = await user_repo.get_by_id(admin_id)
                if not user:
                    from db import models
                    user = models.User(id=admin_id, first_name="Admin", is_premium=False)
                    session.add(user)
                    await session.flush()
                    logger.info(f"✓ Created user for admin: {admin_id}")
                # Ensure admin record exists with owner role
                existing = await admin_repo.get_by_user_id(admin_id)
                if existing:
                    if existing.role != AdminRole.OWNER.value:
                        existing.role = AdminRole.OWNER.value
                        logger.info(f"✓ Updated admin {admin_id} to owner")
                    else:
                        logger.info(f"✓ Admin {admin_id} already registered as owner")
                else:
                    await admin_repo.create(admin_id, role=AdminRole.OWNER.value)
                    logger.info(f"✓ Registered super admin: {admin_id}")
            except Exception as e:
                logger.error(f"Error registering admin {admin_id}: {e}")
                await session.rollback()
                continue
        await session.commit()
        logger.info("Super admin registration complete")


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
    dp.include_router(inline_handlers.router)
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
