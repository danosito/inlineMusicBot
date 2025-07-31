import asyncio
import logging
import os

import redis.asyncio as aioredis
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from dotenv import load_dotenv

from storage import set_redis_client
from commandsModule import router as commands_router
from inlineModule import router as inline_router
from yandexModule import router as yandex_router
from youtubeModule import router as youtube_router
from spotifyModule import router as spotify_router

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    redis_client = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    set_redis_client(redis_client)

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(commands_router)
    dp.include_router(inline_router)
    dp.include_router(yandex_router)
    dp.include_router(spotify_router)
    dp.include_router(youtube_router)

    await bot.set_my_commands([
        BotCommand(command="start", description="Начать"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="token", description="Добавить токен"),
        BotCommand(command="cookie", description="Добавить cookies"),
    ])

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
