from __future__ import annotations

import json
from pathlib import Path
from collections import deque

import aiosqlite

from core.models import Track


class Repository:
    def __init__(self, path: Path):
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS queue (chat_id INTEGER, title TEXT, url TEXT, webpage_url TEXT, duration INTEGER, source TEXT)")
            await db.execute("CREATE TABLE IF NOT EXISTS memory (chat_id INTEGER PRIMARY KEY, context TEXT)")
            await db.execute("CREATE TABLE IF NOT EXISTS stats (user_id INTEGER PRIMARY KEY, score INTEGER DEFAULT 0)")
            await db.commit()

    async def add_track(self, chat_id: int, track: Track) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO queue VALUES (?, ?, ?, ?, ?, ?)", (chat_id, track.title, track.url, track.webpage_url, track.duration, track.source))
            await db.commit()

    async def remove_track(self, chat_id: int, track: Track) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM queue WHERE chat_id = ? AND title = ? AND url = ?", (chat_id, track.title, track.url))
            await db.commit()

    async def clear_queue(self, chat_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM queue WHERE chat_id = ?", (chat_id,))
            await db.commit()

    async def load_queues(self) -> dict[int, list[Track]]:
        queues: dict[int, list[Track]] = {}
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT chat_id, title, url, webpage_url, duration, source FROM queue") as cur:
                async for chat_id, title, url, webpage_url, duration, source in cur:
                    queues.setdefault(chat_id, []).append(Track(title, url, webpage_url or "", duration or 0, source or "yt-dlp"))
        return queues

    async def save_memory(self, chat_id: int, memory: deque[str]) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT OR REPLACE INTO memory VALUES (?, ?)", (chat_id, json.dumps(list(memory), ensure_ascii=False)))
            await db.commit()

    async def load_memories(self) -> dict[int, deque[str]]:
        data: dict[int, deque[str]] = {}
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT chat_id, context FROM memory") as cur:
                async for chat_id, context in cur:
                    data[chat_id] = deque(json.loads(context or "[]"), maxlen=8)
        return data
