from aiogram import Dispatcher, Bot, Router
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import redis.asyncio as redis
from config import settings
import logging

logger = logging.getLogger(__name__)

# Bot instance
bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Redis storage for FSM
async def create_redis_storage():
    """Create Redis storage for FSM."""
    redis_conn = redis.from_url(settings.REDIS_URL)
    return RedisStorage(redis=redis_conn)

# Dispatcher
async def setup_dispatcher():
    """Setup dispatcher with middlewares."""
    # Create storage
    storage = await create_redis_storage()
    
    # Create dispatcher
    dp = Dispatcher(storage=storage)
    
    logger.info("✓ Dispatcher created")
    return dp

# Main router for handlers
router = Router()

async def setup_handlers():
    """Setup all handlers and routers."""
    # Will be populated by handlers from Phase 4+
    logger.info("✓ Handlers setup complete")

async def close_bot():
    """Close bot session."""
    await bot.session.close()
