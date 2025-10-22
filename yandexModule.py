import os
import re
import uuid
import asyncio
import json
import html
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
CAPTION_LIMIT = 1024
CAPTION_OPEN_TAG = "<blockquote expandable>"
CAPTION_CLOSE_TAG = "</blockquote>"


def parse_track_id(text: str) -> Optional[str]:
    m = TRACK_ID_RE.search(text)
    if m:
        return m.group(1)
    if text.isdigit():
        return text
    return None


def _build_caption_pages(raw_lyrics: str) -> List[str]:
    cleaned = raw_lyrics.strip()
    if not cleaned:
        return []
    max_payload = CAPTION_LIMIT - len(CAPTION_OPEN_TAG) - len(CAPTION_CLOSE_TAG)
    if max_payload <= 0:
        return []
    pages: List[str] = []
    current_parts: List[str] = []
    current_len = 0
    last_break: Optional[tuple[int, int]] = None
    for char in cleaned:
        escaped_char = html.escape(char)
        escaped_len = len(escaped_char)
        if current_len + escaped_len > max_payload and current_parts:
            if last_break:
                break_idx, break_len = last_break
                chunk = "".join(current_parts[:break_idx])
                pages.append(f"{CAPTION_OPEN_TAG}{chunk}{CAPTION_CLOSE_TAG}")
                current_parts = current_parts[break_idx:]
                current_len -= break_len
            else:
                pages.append(f"{CAPTION_OPEN_TAG}{''.join(current_parts)}{CAPTION_CLOSE_TAG}")
                current_parts = []
                current_len = 0
            last_break = None
        current_parts.append(escaped_char)
        current_len += escaped_len
        if char in ("\n", " "):
            last_break = (len(current_parts), current_len)
    if current_parts:
        pages.append(f"{CAPTION_OPEN_TAG}{''.join(current_parts)}{CAPTION_CLOSE_TAG}")
    return pages


def _get_caption_pages(info: dict) -> List[str]:
    pages = info.get("caption_pages")
    if pages:
        return pages
    legacy_text = info.get("text")
    if legacy_text:
        return [legacy_text]
    return []


def _build_pagination_keyboard(track_id: str, total_pages: int, current_page: int) -> Optional[InlineKeyboardMarkup]:
    if total_pages <= 1:
        return None
    buttons: List[InlineKeyboardButton] = []
    if current_page > 0:
        prev_page = current_page - 1
        buttons.append(
            InlineKeyboardButton(
                text=f"← Страница {prev_page + 1}",
                callback_data=f"ym_pg:{track_id}:{prev_page}"
            )
        )
    if current_page < total_pages - 1:
        next_page = current_page + 1
        buttons.append(
            InlineKeyboardButton(
                text=f"Страница {next_page + 1} →",
                callback_data=f"ym_pg:{track_id}:{next_page}"
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def _download_track(token: str, track_id: str, dest: str) -> str:
    client = Client(token)
    client.init()
    track = client.tracks([track_id])[0]
    track.download(dest)
    lyrics_text = ""
    try:
        lyrics = track.get_lyrics()
        if lyrics:
            fetched = lyrics.fetch_lyrics()
            if fetched:
                lyrics_text = fetched
    except Exception:
        lyrics_text = ""
    caption_pages = _build_caption_pages(lyrics_text)
    info = {
        "title": track.title,
        "artists": ", ".join(a.name for a in track.artists),
        "caption_pages": caption_pages,
    }
    if caption_pages:
        info["text"] = caption_pages[0]
    return json.dumps(info)


async def download_track(token: str, track_id: str, dest: str) -> dict:
    info_json = await asyncio.to_thread(_download_track, token, track_id, dest)
    return json.loads(info_json)


async def get_track_info(token: str, track_id: str) -> dict:
    cached = await cache_get_ym_info(track_id)
    if cached and "caption_pages" in cached:
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
        pages = _get_caption_pages(info)
        caption = pages[0] if pages else ""
        reply_markup = _build_pagination_keyboard(track_id, len(pages), 0)
        if cb.message:
            await cb.message.edit_text("Отправляю…")
            target = dict(chat_id=cb.message.chat.id, message_id=cb.message.message_id)
        else:
            await cb.bot.edit_message_text(inline_message_id=cb.inline_message_id, text="Отправляю…")
            target = dict(inline_message_id=cb.inline_message_id)
        media_kwargs = dict(
            media=file_id,
            title=info["title"],
            performer=info["artists"],
        )
        if caption:
            media_kwargs["caption"] = caption
            media_kwargs["parse_mode"] = "HTML"
        await cb.bot.edit_message_media(
            media=InputMediaAudio(**media_kwargs),
            reply_markup=reply_markup,
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
    pages = _get_caption_pages(info)
    caption = pages[0] if pages else ""
    reply_markup = _build_pagination_keyboard(track_id, len(pages), 0)
    media_kwargs = dict(
        media=file_id,
        title=info["title"],
        performer=info["artists"],
    )
    if caption:
        media_kwargs["caption"] = caption
        media_kwargs["parse_mode"] = "HTML"
    await cb.bot.edit_message_media(
        media=InputMediaAudio(**media_kwargs),
        reply_markup=reply_markup,
        **target
    )
    await cache_file_set_ym(track_id, file_id)
    await cache_set_ym_info(track_id, info)
    await cb.answer()
    os.remove(path)


async def on_caption_page(cb: CallbackQuery):
    try:
        _, track_id, page_str = cb.data.split(":", 2)
        page_index = int(page_str)
    except (ValueError, AttributeError):
        await cb.answer()
        return
    token = await fetch_ym_token(cb.from_user.id)
    if not token:
        await cb.answer("Нужен токен")
        return
    info = await get_track_info(token, track_id)
    pages = _get_caption_pages(info)
    if not pages:
        await cb.answer("Текст недоступен", show_alert=True)
        return
    total_pages = len(pages)
    if page_index < 0:
        page_index = 0
    if page_index >= total_pages:
        page_index = total_pages - 1
    caption = pages[page_index]
    reply_markup = _build_pagination_keyboard(track_id, total_pages, page_index)
    if cb.message:
        await cb.bot.edit_message_caption(
            chat_id=cb.message.chat.id,
            message_id=cb.message.message_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        await cb.bot.edit_message_caption(
            inline_message_id=cb.inline_message_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    await cb.answer(f"Страница {page_index + 1} из {total_pages}")


router.callback_query.register(on_download, F.data.startswith("ym_dl:"))
router.callback_query.register(on_caption_page, F.data.startswith("ym_pg:"))
