import re
from aiogram import Router

router = Router()

YOUTUBE_PATTERNS = [re.compile(r"https://(?:www\.)?youtube\.com"), re.compile(r"https://youtu\.be")]

def is_youtube_link(text: str) -> bool:
    return any(p.search(text) for p in YOUTUBE_PATTERNS)
