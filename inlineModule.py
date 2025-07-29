from aiogram import Router
from aiogram.types import (
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent
)
import yandexModule as ym
import youtubeModule as yt
import spotifyModule as sf

router = Router()

@router.inline_query()
async def handle_inline(query: InlineQuery):
    text = query.query.strip()
    if text.startswith("https://"):
        if "yandex.ru" in text:
            track_id = ym.parse_track_id(text)
            if track_id:
                await ym.answer_download(query, track_id)
            else:
                await query.answer([
                    InlineQueryResultArticle(
                        id="bad_link",
                        title="Ссылка не ведет на трек",
                        description="Не удалось найти track_id",
                        input_message_content=InputTextMessageContent(message_text="ссылка не ведет на трек"),
                    )
                ], cache_time=1)
        elif yt.is_youtube_link(text):
            await query.answer([
                InlineQueryResultArticle(
                    id="yt_soon",
                    title="YouTube скоро",
                    description="Поддержка YouTube будет скоро",
                    input_message_content=InputTextMessageContent(message_text="YouTube скоро"),
                )
            ], cache_time=1)
        elif sf.is_spotify_link(text):
            await query.answer([
                InlineQueryResultArticle(
                    id="sf_late",
                    title="Spotify не скоро",
                    description="Поддержка Spotify будет нескоро",
                    input_message_content=InputTextMessageContent(message_text="Spotify пока не поддерживается"),
                )
            ], cache_time=1)
        else:
            await query.answer([
                InlineQueryResultArticle(
                    id="not_supported",
                    title="Сервис не поддерживается",
                    description="Эта ссылка не подходит",
                    input_message_content=InputTextMessageContent(message_text="сервис не поддерживается"),
                )
            ], cache_time=1)
    else:
        if text.startswith("ym "):
            results = await ym.search_tracks(text[3:])
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
        elif text.startswith("yt "):
            await query.answer([
                InlineQueryResultArticle(
                    id="yt_search",
                    title="Функция в разработке",
                    description="Поиск по YouTube будет позже",
                    input_message_content=InputTextMessageContent(message_text="функция в разработке"),
                )
            ], cache_time=1)
        elif text.startswith("sf "):
            await query.answer([
                InlineQueryResultArticle(
                    id="sf_search",
                    title="Функция в разработке",
                    description="Поиск по Spotify будет позже",
                    input_message_content=InputTextMessageContent(message_text="функция в разработке"),
                )
            ], cache_time=1)
        else:
            await query.answer([
                InlineQueryResultArticle(
                    id="unknown",
                    title="Непонятный запрос",
                    description="Попробуйте /help в нашем боте",
                    input_message_content=InputTextMessageContent(message_text="не понимаю запрос"),
                )
            ], cache_time=1)
