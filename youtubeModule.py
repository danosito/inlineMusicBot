import re
from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

router = Router()

YOUTUBE_PATTERNS = [re.compile(r"https://(?:www\.)?youtube\.com"), re.compile(r"https://youtu\.be")]

def is_youtube_link(text: str) -> bool:
    return any(p.search(text) for p in YOUTUBE_PATTERNS)

async def answer_search(query: InlineQuery, search_query_text: str):
    await query.answer([
        InlineQueryResultArticle(
            id="yt_search",
            title="Функция в разработке",
            description="Поиск по YouTube будет позже",
            input_message_content=InputTextMessageContent(message_text="функция в разработке"),
        )
    ], cache_time=1)