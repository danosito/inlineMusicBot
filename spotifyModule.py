import re
from aiogram import Router
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineQuery

router = Router()

SPOTIFY_PATTERN = re.compile(r"https://(?:open\.)?spotify\.com")

def is_spotify_link(text: str) -> bool:
    return bool(SPOTIFY_PATTERN.search(text))

async def answer_search(query: InlineQuery, search_query_text: str):
    await query.answer([
        InlineQueryResultArticle(
            id="sf_search",
            title="Функция в разработке",
            description="Поиск по Spotify будет позже",
            input_message_content=InputTextMessageContent(message_text="функция в разработке"),
        )
    ], cache_time=1)

async def answer_download(query: InlineQuery, link: str):
    await query.answer([
        InlineQueryResultArticle(
            id="sf_late",
            title="Spotify не скоро",
            description="Поддержка Spotify будет нескоро",
            input_message_content=InputTextMessageContent(message_text="Spotify пока не поддерживается"),
        )
    ], cache_time=1)