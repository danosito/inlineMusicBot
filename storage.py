import os
import json
from contextlib import asynccontextmanager
from typing import Optional

import aiosqlite
import redis.asyncio as aioredis

DB_DIR = os.getenv("DB_DIR", "/app/db")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "users.db")

redis_client: aioredis.Redis | None = None

def set_redis_client(client: aioredis.Redis):
    global redis_client
    redis_client = client

@asynccontextmanager
async def with_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                ym_token TEXT,
                pref_service TEXT DEFAULT NULL
            );
            """
        )
        await db.commit()
        yield db

async def save_ym_token(user_id: int, token: str):
    async with with_db() as db:
        await db.execute(
            """
            INSERT INTO users (user_id, ym_token)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET ym_token=excluded.ym_token
            """,
            (user_id, token),
        )
        await db.commit()

async def fetch_ym_token(user_id: int) -> Optional[str]:
    async with with_db() as db:
        async with db.execute(
            "SELECT ym_token FROM users WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def save_pref_service(user_id: int, pref_service: str):
    async with with_db() as db:
        await db.execute(
            """
            INSERT INTO users (user_id, pref_service)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET pref_service=excluded.pref_service
            """,
            (user_id, pref_service),
        )
        await db.commit()

async def get_pref_service(user_id: int):
    async with with_db() as db:
        async with db.execute(
            "SELECT pref_service FROM users WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def cache_get_ym_info(track_id: str) -> Optional[dict]:
    if redis_client is None:
        return None
    data = await redis_client.get(f"track_ym:{track_id}")
    return json.loads(data) if data else None

async def cache_set_ym_info(track_id: str, info: dict):
    if redis_client is None:
        return
    await redis_client.setex(f"track_ym:{track_id}", 24 * 3600, json.dumps(info))

async def cache_file_get_ym(track_id: str) -> Optional[str]:
    if redis_client is None:
        return None
    return await redis_client.get(f"file_ym:{track_id}")

async def cache_file_set_ym(track_id: str, file_id: str):
    if redis_client is None:
        return
    await redis_client.set(f"file_ym:{track_id}", file_id)
