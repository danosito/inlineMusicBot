import datetime
import os
import re
import uuid

import yt_dlp
from aiogram import Router, F
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, \
    InlineKeyboardButton, InlineQueryResultPhoto, CallbackQuery, InputMediaAudio, InputMediaVideo, FSInputFile
import json
import urllib.request
import urllib.parse

from urllib.parse import urlparse, parse_qs

OEMBED = "https://www.youtube.com/oembed"

router = Router()

YOUTUBE_PATTERNS = [re.compile(r"https://(?:www\.)?youtube\.com"), re.compile(r"https://youtu\.be")]
vidInfos = {}

class _StatusLogger:
    """
    Перехватывает сообщения yt-dlp и выводит изменения
    красным цветом (ANSI 31m).
    """

    def __init__(self, cb: CallbackQuery) -> None:
        self._last = None
        self._last_time = datetime.datetime(1970, 1, 1, 0, 0, 0)
        self._cb = cb

    def _print(self, msg: str) -> None:
        now = datetime.datetime.now()
        if msg != self._last and now - self._last_time > datetime.timedelta(milliseconds=500):
            print(f"\033[31m{msg}\033[0m")
            self._cb.message.edit_text(msg)
            self._last = msg
            self._last_time = now

    debug = info = warning = error = _print

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

async def download_video(url: str, fmt: str, cb: CallbackQuery, vid: str) -> dict:
    """
    Скачивает ролик / аудиодорожку во временный каталог.

    Параметры
    ----------
    url      – ссылка на ролик
    fmt      – 'audio'  ▸ MP3 bestaudio
               '<num>'  ▸ MP4 указанной высоты (1080, 720…)

    Возврат
    -------
    {'type': 'audio'|'video', 'file': '/tmp/<id>.<ext>', 'id': <video_id>}
    """

    target_dir = "/tmp"
    os.makedirs(target_dir, exist_ok=True)
    outtmpl = os.path.join(target_dir, f"{vid}.%(ext)s")

    # ─── Формат, пост-процессоры, результ. расширение ───
    if fmt == "audio":
        dl_format = "bestaudio/best"
        post = [{"key": "FFmpegExtractAudio",
                 "preferredcodec": "mp3",
                 "preferredquality": "192"}]
        ext, mediatype = "mp3", "audio"
    else:
        target = re.sub(r"[^\d]", "", fmt) or "720"
        dl_format = (
            f"bestvideo[height<={target}][ext=mp4]+bestaudio[ext=m4a]/"
            f"best[height<={target}][ext=mp4]/"
            f"best[height<={target}]"
        )
        post, ext, mediatype = [], "mp4", "video"

    logger = _StatusLogger(cb)

    ydl_opts = {
        "format": dl_format,
        "outtmpl": outtmpl,
        "logger": logger,
        "postprocessors": post,
        # подавим лишний шелл-вывод FFmpeg
        "postprocessor_args": ["-loglevel", "error"],
        # ускоряем фильтром только нужных форматов
        "merge_output_format": "mp4",
        "quiet": True,
        "nocheckcertificate": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    final_path = os.path.join(target_dir, f"{vid}.{ext}")
    return {"type": mediatype, "file": final_path, "id": vid}


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
    vidInfos[video_id] = info
    message_text = f"{info['title']} — {info['author']}"
    await query.answer([
        InlineQueryResultPhoto(
            id=str(uuid.uuid4()),
            photo_url=info["preview"],
            thumbnail_url=info["preview"],
            caption=message_text,
            title=message_text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=
                [
                    [InlineKeyboardButton(
                        text="Скачать mp3",
                        callback_data=f"yt_dl:{info['id']}:audio"
                    )]
                ] + [
                    [InlineKeyboardButton(
                        text=f"Скачать mp4 {resolution}p",
                        callback_data=f"yt_dl:{info['id']}:{resolution}"
                    )] for resolution in info["resolutions"]
                ]

            )
        )
    ], cache_time=1)


async def on_download(cb: CallbackQuery):
    _, video_id, format = cb.data.split(":")
    info = vidInfos[video_id]
    if cb.message:
        await cb.message.edit_text("Скачиваю UwU…")
        target = dict(chat_id=cb.message.chat.id, message_id=cb.message.message_id)
    else:
        await cb.bot.edit_message_text(inline_message_id=cb.inline_message_id, text="Скачиваю UwU…")
        target = dict(inline_message_id=cb.inline_message_id)
    result = await download_video(video_id, format, cb, video_id)
    if result["type"] == "video":
        sent = await cb.bot.send_video(
            1210881411,
            video=FSInputFile(result["file"])
        )
        await cb.bot.edit_message_media(
            media=InputMediaVideo(media=sent.video.file_id),
            **target
        )
    elif result["type"] == "audio":
        sent = await cb.bot.send_audio(
            1210881411,
            audio=FSInputFile(result["file"]),
            title=info["title"],
            performer=info["author_name"],
        )
        await cb.bot.edit_message_media(
            media=InputMediaAudio(media=sent.audio.file_id, title=info["title"], performer=info["author_name"]),
            **target
        )


router.callback_query.register(on_download, F.data.startswith("yt_dl:"))
