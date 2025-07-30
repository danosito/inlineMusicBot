import re
import uuid

from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, \
    InlineKeyboardButton, InlineQueryResultPhoto
import json
import urllib.request
import urllib.parse

from urllib.parse import urlparse, parse_qs

OEMBED = "https://www.youtube.com/oembed"

router = Router()

YOUTUBE_PATTERNS = [re.compile(r"https://(?:www\.)?youtube\.com"), re.compile(r"https://youtu\.be")]


def is_youtube_link(text: str) -> bool:
    return any(p.search(text) for p in YOUTUBE_PATTERNS)


def extract_video_id(url):
    # Проверяем, если это короткая ссылка типа youtu.be
    parsed_url = urlparse(url)

    if 'youtu.be' in parsed_url.netloc:
        return parsed_url.path.lstrip('/')

    if 'youtube.com' in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        if 'v' in query_params:
            return query_params['v'][0]

        # Иногда ID может быть в пути, например /embed/dQw4w9WgXcQ
        match = re.search(r'/embed/([^/?]+)', parsed_url.path)
        if match:
            return match.group(1)

    return None


async def short_info(url: str, *, timeout: float = 2.0) -> dict:
    """
    Возвращает лёгкую карточку ролика
    (title / autor / preview) за ~0.1 с.
    """
    qs = urllib.parse.urlencode({"url": url, "format": "json"})
    with urllib.request.urlopen(f"{OEMBED}?{qs}", timeout=timeout) as r:
        data = json.load(r)

    return {
        "title": data.get("title"),
        "author": data.get("author_name"),
        "preview": data.get("thumbnail_url"),
        # статичный список, который отобразим юзеру
        "resolutions": [144, 240, 360, 480, 720, 1080],
        "id": extract_video_id(url),
    }


async def answer_search(query: InlineQuery, search_query_text: str):
    await query.answer([
        InlineQueryResultArticle(
            id="yt_search",
            title="Функция в разработке",
            description="Поиск по YouTube будет позже",
            input_message_content=InputTextMessageContent(message_text="функция в разработке"),
        )
    ], cache_time=1)


async def answer_download(query: InlineQuery, link: str):
    video_id = extract_video_id(link)
    if not video_id:
        await query.answer([
            InlineQueryResultArticle(
                id="not_found",
                title="Это не видео",
                description="Не смог извлечь видео, проверьте ссылку",
                input_message_content=InputTextMessageContent(message_text="Не смог извлечь видео, проверьте ссылку"),
            )
        ], cache_time=1)
    info = await short_info(link)
    message_text = f"{info['title']} — {info['author']}"
    await query.answer([
        InlineQueryResultPhoto(
            id=str(uuid.uuid4()),
            photo_url=info["preview"],
            thumb_url=info["preview"],
            title=message_text,
            caption=message_text,
            description="Нажмите кнопку для скачивания",
            input_message_content=InputTextMessageContent(message_text=message_text),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                                                   InlineKeyboardButton(text="Скачать mp3",
                                                                                        callback_data=f"yt_dl:{info['id']}:audio")
                                                               ] + [InlineKeyboardButton(
                text=f"Скачать mp4 {resolution}p", callback_data=f"yt_dl:{info['id']}:{resolution}") for resolution in
                                                                    info["resolutions"]]]),
        )
    ], cache_time=1)
