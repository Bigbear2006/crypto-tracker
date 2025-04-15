import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from bot.settings import settings

logger = logging.getLogger('bot')
loop = asyncio.get_event_loop()

bot = Bot(settings.BOT_TOKEN)
storage = RedisStorage.from_url(settings.REDIS_URL)
dp = Dispatcher(storage=storage)
