import datetime
import json
import os
import re
import urllib.request
import urllib.parse

from urllib.parse import urlparse, parse_qs
import yt_dlp
from aiogram.types import InlineQuery

OEMBED = "https://www.youtube.com/oembed"


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


def short_info(url: str, *, timeout: float = 2.0) -> dict:
    """
    Возвращает лёгкую карточку ролика
    (title / autor / preview) за ~0.1 с.
    """
    qs = urllib.parse.urlencode({"url": url, "format": "json"})
    with urllib.request.urlopen(f"{OEMBED}?{qs}", timeout=timeout) as r:
        data = json.load(r)

    return {
        "title": data.get("title"),
        "autor": data.get("author_name"),
        "preview": data.get("thumbnail_url"),
        # статичный список, который отобразим юзеру
        "resolutions": [144, 240, 360, 480, 720, 1080],
    }


# ──────────────────────────────────────────────────────────────
# 2. download_video
# ──────────────────────────────────────────────────────────────
class _StatusLogger:
    """
    Перехватывает сообщения yt-dlp и выводит изменения
    красным цветом (ANSI 31m).
    """

    def __init__(self) -> None:
        self._last = None
        self._last_time = datetime.datetime(1970, 1, 1, 0, 0, 0)

    def _print(self, msg: str) -> None:
        now = datetime.datetime.now()
        if msg != self._last and now - self._last_time > datetime.timedelta(milliseconds=500):
            print(f"\033[31m{msg}\033[0m")
            self._last = msg
            self._last_time = now

    debug = info = warning = error = _print


def download_video(url: str, fmt: str, query: InlineQuery) -> dict:
    """
    Скачивает ролик / аудиодорожку во временный каталог.

    Параметры
    ----------
    url      – ссылка на ролик
    fmt      – 'audio'  ▸ MP3 bestaudio
               '<num>'  ▸ MP4 указанной высоты (1080, 720…)
    query    – объект InlineQuery; на проде через него
               обновляется статус. Здесь он не используется.

    Возврат
    -------
    {'type': 'audio'|'video', 'file': '/tmp/<id>.<ext>', 'id': <video_id>}
    """
    vid = extract_video_id(url)
    if not vid:
        raise ValueError("Не удалось извлечь video-id из URL")

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

    logger = _StatusLogger()

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
