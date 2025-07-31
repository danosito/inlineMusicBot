import os
import re
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode

from storage import save_ym_token, save_pref_service, get_pref_service

router = Router()

class TokenState(StatesGroup):
    waiting_token: State = State()


class CookieState(StatesGroup):
    waiting_file: State = State()

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


@router.message(Command("cookie"))
async def cmd_cookie(msg: Message, state: FSMContext):
    await msg.answer(
        "Скачайте расширение для экспорта cookies.txt:\n"
        "Firefox: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/\n"
        "Chrome: https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc\n"
        "Экспортируйте cookies для youtube.com и отправьте файл сюда.",
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(CookieState.waiting_file)

def pref_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Яндекс Музыка", callback_data="pref_ym")],
            [InlineKeyboardButton(text="YouTube", callback_data="pref_yt")],
            [InlineKeyboardButton(text="Spotify", callback_data="pref_sf")]
        ]
    )

@router.message(Command("pref"))
async def set_pref(msg: Message, state: FSMContext):
    await msg.answer(
        "Выберите предпочтительный сервис для загрузки",
        reply_markup=pref_keyboard()
    )


@router.callback_query(F.data.contains("pref"))
async def handle_ym(call: CallbackQuery):
    await save_pref_service(call.from_user.id, call.data.split("_")[1])
    await call.answer(f"saved service: {await get_pref_service(call.from_user.id)}")

@router.message(TokenState.waiting_token)
async def save_user_token(msg: Message, state: FSMContext):
    token = msg.text.strip()
    if not re.match(r"^y0[-_0-9A-Za-z]+$", token):
        await msg.reply("Это не похоже на токен. Попробуйте снова.")
        return
    await save_ym_token(msg.from_user.id, token)
    await msg.reply("Токен сохранён!")
    await state.clear()


@router.message(CookieState.waiting_file, F.document)
async def save_cookie_file(msg: Message, state: FSMContext):
    if not msg.document.file_name.endswith(".txt"):
        await msg.reply("Нужен файл cookies.txt.")
        return
    os.makedirs("/app/cookies", exist_ok=True)
    path = f"/app/cookies/{msg.from_user.id}.txt"
    await msg.bot.download(msg.document.file_id, destination=path)
    await msg.reply("Cookies сохранены.")
    await state.clear()


@router.message(CookieState.waiting_file)
async def request_cookie_file(msg: Message):
    await msg.reply("Пожалуйста, отправьте файл cookies.txt.")

@router.message(F.text.startswith("/"))
async def unknown_command(msg: Message):
    await msg.reply("Неизвестная команда. Попробуйте /start.")
