import os
import re
import uuid
import asyncio
import json
from typing import Optional, List

from aiogram import Router, F
from aiogram.types import (
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
    FSInputFile, InputMediaAudio
)
from yandex_music import Client

from storage import fetch_ym_token, cache_get_ym_info, cache_set_ym_info, cache_file_get_ym, cache_file_set_ym

router = Router()

TRACK_ID_RE = re.compile(r"(?:/track/)(\d+)")
TOKEN_RE = re.compile(r"^y0[-_0-9A-Za-z]+$")


def parse_track_id(text: str) -> Optional[str]:
    m = TRACK_ID_RE.search(text)
    if m:
        return m.group(1)
    if text.isdigit():
        return text
    return None


def _download_track(token: str, track_id: str, dest: str) -> str:
    client = Client(token)
    client.init()
    track = client.tracks([track_id])[0]
    track.download(dest)
    info = {
        "title": track.title,
        "artists": ", ".join(a.name for a in track.artists),
        "text": track.get_lyrics().fetch_lyrics()[:1000]
    }
    return json.dumps(info)


async def download_track(token: str, track_id: str, dest: str) -> dict:
    info_json = await asyncio.to_thread(_download_track, token, track_id, dest)
    return json.loads(info_json)


async def get_track_info(token: str, track_id: str) -> dict:
    cached = await cache_get_ym_info(track_id)
    if cached:
        return cached
    dest = os.path.join("/tmp", f"tmp_{track_id}.mp3")
    info = await download_track(token, track_id, dest)
    os.remove(dest)
    await cache_set_ym_info(track_id, info)
    return info


async def search_tracks(query: str, token: str) -> List[InlineQueryResultArticle]:
    client = Client(token)
    client.init()
    res = client.search(query)
    try:
        tracks = res["tracks"]["results"][:10]
    except TypeError:
        return []
    items: List[InlineQueryResultArticle] = []
    for tr in tracks:
        track_id = str(tr["id"])
        title = tr["title"]
        artists = ", ".join(a["name"] for a in tr["artists"])
        try:
            cover = tr["cover_uri"].replace("%%", "100x100")
        except KeyError:
            cover = ""
        if cover:
            cover = "https://" + cover
        msg = f"{artists} — {title}"
        items.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=msg,
                description="Нажмите кнопку для скачивания",
                input_message_content=InputTextMessageContent(message_text=msg),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="Скачать", callback_data=f"ym_dl:{track_id}")
                ]]),
                thumb_url=cover
            )
        )
    return items


async def answer_download(query: InlineQuery, track_id: str):
    token = await fetch_ym_token(query.from_user.id)
    bot_username = (await query.bot.me()).username
    if not token:
        text = f"Чтобы скачать трек, откройте @{bot_username} и отправьте /token"
        await query.answer([
            InlineQueryResultArticle(
                id="need_token",
                title="Добавьте токен",
                description="Нет токена для скачивания",
                input_message_content=InputTextMessageContent(message_text=text),
            )
        ], cache_time=1)
        return
    info = await get_track_info(token, track_id)
    message_text = f"{info['artists']} — {info['title']}"
    await query.answer([
        InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=message_text,
            description="Нажмите кнопку для скачивания",
            input_message_content=InputTextMessageContent(message_text=message_text),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Скачать", callback_data=f"ym_dl:{track_id}")
            ]]),
        )
    ], cache_time=1)


async def answer_search(query: InlineQuery, search_query_text: str):
    token = await fetch_ym_token(query.from_user.id)
    bot_username = (await query.bot.me()).username
    if not token:
        text = f"Чтобы скачать трек, откройте @{bot_username} и отправьте /token"
        await query.answer([
            InlineQueryResultArticle(
                id="need_token",
                title="Добавьте токен",
                description="Нет токена для скачивания",
                input_message_content=InputTextMessageContent(message_text=text),
            )
        ], cache_time=1)
        return
    results = await search_tracks(search_query_text, token)

    if results:
        await query.answer(results, cache_time=1)
    else:
        await query.answer([
            InlineQueryResultArticle(
                id="no_results",
                title="Ничего не найдено",
                description="Попробуйте другой запрос",
                input_message_content=InputTextMessageContent(message_text="ничего не найдено"),
            )
        ], cache_time=1)


async def on_download(cb: CallbackQuery):
    track_id = cb.data.split(":", 1)[1]
    token = await fetch_ym_token(cb.from_user.id)
    if not token:
        return await cb.answer("Нужен токен")

    file_id = await cache_file_get_ym(track_id)
    if file_id:
        info = await get_track_info(token, track_id)
        if cb.message:
            await cb.message.edit_text("Отправляю…")
            target = dict(chat_id=cb.message.chat.id, message_id=cb.message.message_id)
        else:
            await cb.bot.edit_message_text(inline_message_id=cb.inline_message_id, text="Отправляю…")
            target = dict(inline_message_id=cb.inline_message_id)
        await cb.bot.edit_message_media(
            media=InputMediaAudio(
                media=file_id,
                title=info["title"],
                performer=info["artists"],
                caption=info["text"]
            ),
            **target
        )
        await cb.answer()
        return
    if cb.message:
        await cb.message.edit_text("Скачиваю…")
        target = dict(chat_id=cb.message.chat.id, message_id=cb.message.message_id)
    else:
        await cb.bot.edit_message_text(inline_message_id=cb.inline_message_id, text="Скачиваю…")
        target = dict(inline_message_id=cb.inline_message_id)
    path = f"/tmp/{track_id}_{cb.from_user.id}.mp3"
    info = await download_track(token, track_id, path)
    sent = await cb.bot.send_audio(
        1210881411,
        audio=FSInputFile(path),
        title=info["title"],
        performer=info["artists"],
    )
    file_id = sent.audio.file_id
    await cb.bot.edit_message_media(
        media=InputMediaAudio(media=file_id, title=info["title"], performer=info["artists"],
                              caption=info["text"]),
        **target
    )
    await cache_file_set_ym(track_id, file_id)
    await cb.answer()
    os.remove(path)


router.callback_query.register(on_download, F.data.startswith("ym_dl:"))
