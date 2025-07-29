import os
import re
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.enums import ParseMode

from storage import save_token

router = Router()

class TokenState(StatesGroup):
    waiting_token: State = State()

@router.message(CommandStart())
async def cmd_start(msg: Message):
    bot_username = (await msg.bot.me()).username
    await msg.answer(
        "Привет! Я могу искать музыку и скачивать треки из разных сервисов.\n"
        f"В чатах используйте @{bot_username} и ссылку или запрос."
    )

@router.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer(
        "Через инлайн режим можно скачивать треки из Яндекс Музыки.\n"
        "Используйте префикс `ym` для поиска. Поддержка YouTube скоро, Spotify позднее.",
        parse_mode=ParseMode.MARKDOWN,
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
    if not re.match(r"^y0[-_0-9A-Za-z]+$", token):
        await msg.reply("Это не похоже на токен. Попробуйте снова.")
        return
    await save_token(msg.from_user.id, token)
    await msg.reply("Токен сохранён!")
    await state.clear()

@router.message(F.text.startswith("/"))
async def unknown_command(msg: Message):
    await msg.reply("Неизвестная команда. Попробуйте /start.")
