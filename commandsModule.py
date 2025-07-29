import re
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode

from storage import save_ym_token, save_pref_service

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
    await call.answer(f"call: {call.data}")
    await save_pref_service(call.from_user.id, call.data.split("_")[1])

@router.message(TokenState.waiting_token)
async def save_user_token(msg: Message, state: FSMContext):
    token = msg.text.strip()
    if not re.match(r"^y0[-_0-9A-Za-z]+$", token):
        await msg.reply("Это не похоже на токен. Попробуйте снова.")
        return
    await save_ym_token(msg.from_user.id, token)
    await msg.reply("Токен сохранён!")
    await state.clear()

@router.message(F.text.startswith("/"))
async def unknown_command(msg: Message):
    await msg.reply("Неизвестная команда. Попробуйте /start.")
