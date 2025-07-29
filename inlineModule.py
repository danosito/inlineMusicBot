from aiogram import Router
from aiogram.types import (
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent
)
import yandexModule as ym
import youtubeModule as yt
import spotifyModule as sf
from storage import get_pref_service
from yandexModule import answer_search as answer_search_ym
from youtubeModule import answer_search as answer_search_yt
from spotifyModule import answer_search as answer_search_sf

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
            await answer_search_ym(query, text[3:])
        elif text.startswith("yt "):
            await answer_search_yt(query, text[3:])
        elif text.startswith("sf "):
            await answer_search_sf(query, text[3:])
        else:
            pref = get_pref_service(query.from_user.id)
            if pref:
                match pref:
                    case "ym":
                        await answer_search_ym(query, text[3:])
                    case "yt":
                        await answer_search_yt(query, text[3:])
                    case "sf":
                        await answer_search_sf(query, text[3:])
                    case _:
                        await query.answer([
                            InlineQueryResultArticle(
                                id="unknown",
                                title="Выбран неправильный сервис в предпочтительном",
                                description="Попробуйте /help в нашем боте",
                                input_message_content=InputTextMessageContent(message_text="не понимаю запрос"),
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
