from aiogram import Dispatcher, Bot, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import settings
import logging

logger = logging.getLogger(__name__)

# Bot instance
bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)


async def create_storage():
    """Create FSM storage. Prefer Redis, fallback to Memory."""
    redis_url = settings.FIXED_REDIS_URL
    if redis_url:
        try:
            from aiogram.fsm.storage.redis import RedisStorage
            import redis.asyncio as aioredis
            redis_conn = aioredis.from_url(redis_url)
            await redis_conn.ping()
            logger.info("✓ Redis storage connected")
            return RedisStorage(redis=redis_conn)
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}), falling back to MemoryStorage")
    return MemoryStorage()


async def setup_dispatcher():
    """Setup dispatcher with storage."""
    storage = await create_storage()
    dp = Dispatcher(storage=storage)
    logger.info("✓ Dispatcher created")
    return dp


# Main router (unused, each handler file defines its own)
router = Router()


async def close_bot():
    """Close bot session."""
    await bot.session.close()
