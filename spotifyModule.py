import re
from aiogram import Router

router = Router()

SPOTIFY_PATTERN = re.compile(r"https://(?:open\.)?spotify\.com")

def is_spotify_link(text: str) -> bool:
    return bool(SPOTIFY_PATTERN.search(text))
