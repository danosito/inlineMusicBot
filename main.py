import asyncio
import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import aiosqlite
import redis.asyncio as aioredis
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Message, FSInputFile, InputMediaAudio,
)
from dotenv import load_dotenv
from yandex_music import Client

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DB_DIR = os.getenv("DB_DIR", "/app/db")
ADMIN_CONTACT = "@admin"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


# ─── Database helpers ──────────────────────────────────────────────────────────
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "tokens.db")


@asynccontextmanager
async def with_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                user_id INTEGER PRIMARY KEY,
                token TEXT
            );
            """
        )
        await db.commit()
        yield db


async def save_token(user_id: int, token: str):
    async with with_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO tokens (user_id, token) VALUES (?, ?)",
            (user_id, token),
        )
        await db.commit()


async def fetch_token(user_id: int) -> Optional[str]:
    async with with_db() as db:
        async with db.execute(
            "SELECT token FROM tokens WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


# ─── Redis cache ───────────────────────────────────────────────────────────────
redis_client: aioredis.Redis


async def cache_get(track_id: str) -> Optional[dict]:
    data = await redis_client.get(f"track:{track_id}")
    return json.loads(data) if data else None


async def cache_set(track_id: str, info: dict):
    await redis_client.setex(f"track:{track_id}", 24 * 3600, json.dumps(info))


# ─── Yandex helpers ────────────────────────────────────────────────────────────

TRACK_ID_RE = re.compile(r"(?:/track/)(\d+)")
TOKEN_RE = re.compile(r"^y0[-_0-9A-Za-z]+$")


def _download_track(token: str, track_id: str, dest: str) -> str:
    client = Client(token)
    client.init()
    track = client.tracks([track_id])[0]
    track.download(dest)
    info = {
        "title": track.title,
        "artists": ", ".join(a.name for a in track.artists)
    }
    return json.dumps(info)


async def download_track(token: str, track_id: str, dest: str) -> dict:
    info_json = await asyncio.to_thread(_download_track, token, track_id, dest)
    return json.loads(info_json)


async def get_track_info(token: str, track_id: str) -> dict:
    cached = await cache_get(track_id)
    if cached:
        return cached
    dest = os.path.join("/tmp", f"tmp_{track_id}.mp3")
    info = await download_track(token, track_id, dest)
    os.remove(dest)
    await cache_set(track_id, info)
    return info


# ─── FSM for token ─────────────────────────────────────────────────────────────
class TokenState(StatesGroup):
    waiting_token: State = State()


# ─── Telegram router ───────────────────────────────────────────────────────────
router = Dispatcher()


@router.message(CommandStart())
async def cmd_start(msg: Message):
    await msg.answer(
        "Привет! Я могу скачивать треки из Яндекс Музыки в инлайн режиме.\n"
        "Отправьте в любом чате `@" + (await msg.bot.me()).username + " <ссылка на трек>`.",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer(
        "Отправьте ссылку на трек через инлайн режим, и получите кнопку для скачивания.\n"
        "Чтобы добавить токен Яндекс Музыки, используйте команду /token.",
    )


@router.message(Command("token"))
async def cmd_token(msg: Message, state: FSMContext):
    await msg.answer(
        "Инструкция по получению токена: https://yandex-music.readthedocs.io/en/main/token.html\n"
        "Отправьте полученный токен одним сообщением."
    )
    await state.set_state(TokenState.waiting_token)


@router.message(TokenState.waiting_token)
async def save_user_token(msg: Message, state: FSMContext):
    token = msg.text.strip()
    if not TOKEN_RE.match(token):
        await msg.reply("Это не похоже на токен. Попробуйте снова.")
        return
    await save_token(msg.from_user.id, token)
    await msg.reply("Токен сохранён!")
    await state.clear()


@router.message(F.text.startswith("/"))
async def unknown_command(msg: Message):
    await msg.reply("Неизвестная команда. Попробуйте /start.")


# ─── Inline mode ───────────────────────────────────────────────────────────────


def parse_track_id(text: str) -> Optional[str]:
    m = TRACK_ID_RE.search(text)
    if m:
        return m.group(1)
    if text.isdigit():
        return text
    return None


@router.inline_query()
async def inline_download(query: InlineQuery):
    track_id = parse_track_id(query.query.strip())
    if not track_id:
        await query.answer([], cache_time=1)
        return

    token = await fetch_token(query.from_user.id)
    bot_username = (await query.bot.me()).username

    if not token:
        text = (
            f"Чтобы скачать трек, откройте @{bot_username} и отправьте /token"
        )
        await query.answer([
            InlineQueryResultArticle(
                id="need_token",
                title="Добавьте токен",
                description="Нет токена для скачивания",
                input_message_content=InputTextMessageContent(message_text=text),
            )
        ], cache_time=1)
        return

    # have token, show download button
    info = await get_track_info(token, track_id)
    message_text = f"{info['artists']} — {info['title']}"
    await query.answer([
        InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=message_text,
            description="Нажмите кнопку для скачивания",
            input_message_content=InputTextMessageContent(message_text=message_text),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Скачать", callback_data=f"dl:{track_id}")
            ]]),
        )
    ], cache_time=1)


@router.callback_query(F.data.startswith("dl:"))
async def on_download(cb: CallbackQuery):
    track_id = cb.data.split(":", 1)[1]
    token = await fetch_token(cb.from_user.id)
    if not token:
        return await cb.answer("Нужен токен")

    # 1. Показать «Скачиваю…»
    if cb.message:          # кнопка под обычным сообщением
        await cb.message.edit_text("Скачиваю…")
        target = dict(chat_id=cb.message.chat.id,
                      message_id=cb.message.message_id)
    else:                   # кнопка в inline‑сообщении
        await cb.bot.edit_message_text(
            inline_message_id=cb.inline_message_id,
            text="Скачиваю…"
        )
        target = dict(inline_message_id=cb.inline_message_id)

    # 2. Скачиваем трек
    path = f"/tmp/{track_id}_{cb.from_user.id}.mp3"
    info = await download_track(token, track_id, path)

    # 3. Отправляем аудио пользователю, чтобы получить file_id
    sent = await cb.bot.send_audio(
        cb.from_user.id,
        audio=FSInputFile(path),
        title=info["title"],
        performer=info["artists"],
    )
    file_id = sent.audio.file_id

    # 4. Заменяем медиа сообщения на полученное аудио
    await cb.bot.edit_message_media(
        media=InputMediaAudio(
            media=file_id,
            title=info["title"],
            performer=info["artists"]
        ),
        **target
    )
    await cb.answer()
    os.remove(path)


async def main():
    global redis_client
    redis_client = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

    bot = Bot(BOT_TOKEN)
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="token", description="Добавить токен"),
    ])
    await router.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
