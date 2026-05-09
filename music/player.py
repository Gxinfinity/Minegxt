from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import defaultdict
from contextlib import suppress
from urllib.parse import urlparse

from yt_dlp import YoutubeDL

from core.config import Settings
from core.models import Track
from database.repository import Repository

log = logging.getLogger("ruhi.music")

METADATA_ONLY = ("spotify.com", "open.spotify.com", "music.apple.com", "deezer.com", "jiosaavn.com", "saavn.com")


class MusicPlayer:
    def __init__(self, calls, settings: Settings, repo: Repository):
        self.calls = calls
        self.settings = settings
        self.repo = repo
        self.queues: dict[int, list[Track]] = defaultdict(list)
        self.active: set[int] = set()
        self.locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.started_at: dict[int, float] = defaultdict(float)
        self.volume: dict[int, int] = defaultdict(lambda: 100)
        self.paused: set[int] = set()

    async def load(self) -> None:
        self.queues.update(await self.repo.load_queues())

    async def join(self, chat_id: int) -> None:
        if chat_id in self.active:
            return
        await self.calls.play(chat_id, self.settings.empty_audio)
        self.active.add(chat_id)

    async def leave(self, chat_id: int) -> None:
        with suppress(Exception):
            if hasattr(self.calls, "leave_call"):
                await self.calls.leave_call(chat_id)
            elif hasattr(self.calls, "leave_group_call"):
                await self.calls.leave_group_call(chat_id)
        self.active.discard(chat_id)
        self.paused.discard(chat_id)

    async def add(self, chat_id: int, query: str) -> list[Track]:
        tracks = await self.resolve(query)
        if not tracks:
            return []
        room = self.settings.max_queue - len(self.queues[chat_id])
        added = tracks[: max(0, room)]
        for track in added:
            self.queues[chat_id].append(track)
            await self.repo.add_track(chat_id, track)
        await self.join(chat_id)
        if len(self.queues[chat_id]) == len(added):
            await self.play_current(chat_id)
        return added

    async def resolve(self, query: str) -> list[Track]:
        playlist = any(x in query.lower() for x in ("list=", "playlist", "/album/", "/sets/"))
        target = query if query.startswith("http") else f"ytsearch1:{query}"
        opts = {"quiet": True, "format": "bestaudio/best", "noplaylist": not playlist, "ignoreerrors": True, "default_search": "ytsearch"}
        with YoutubeDL(opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, target, download=False)
        if not info:
            return []
        entries = info.get("entries") or [info]
        out: list[Track] = []
        for entry in entries[: self.settings.max_playlist]:
            track = await self._entry_to_track(entry, query)
            if track:
                out.append(track)
        return out

    async def _entry_to_track(self, entry: dict | None, original: str) -> Track | None:
        if not entry:
            return None
        webpage = entry.get("webpage_url") or entry.get("original_url") or original
        domain = urlparse(webpage).netloc.lower().replace("www.", "")
        title = entry.get("title") or entry.get("fulltitle") or original
        raw_url = entry.get("url")
        if any(host in domain or host in original.lower() for host in METADATA_ONLY) or not raw_url:
            artist = entry.get("artist") or entry.get("uploader") or ""
            return await self._youtube_fallback(f"{title} {artist}".strip())
        return Track(title=title, url=raw_url, webpage_url=webpage, duration=int(entry.get("duration") or 0), source=domain or "direct")

    async def _youtube_fallback(self, query: str) -> Track | None:
        opts = {"quiet": True, "format": "bestaudio/best", "noplaylist": True, "ignoreerrors": True}
        with YoutubeDL(opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch1:{query}", download=False)
        if not info:
            return None
        entry = next((item for item in (info.get("entries") or [info]) if item), None)
        if not entry or not entry.get("url"):
            return None
        return Track(
            title=entry.get("title") or query,
            url=entry["url"],
            webpage_url=entry.get("webpage_url") or "",
            duration=int(entry.get("duration") or 0),
            source="YouTube fallback",
        )

    async def play_current(self, chat_id: int, seek: int = 0) -> bool:
        async with self.locks[chat_id]:
            if not self.queues[chat_id]:
                await self.leave(chat_id)
                return False
            await self.join(chat_id)
            track = self.queues[chat_id][0]
            source = track.url
            if seek and track.webpage_url:
                source = f"{track.webpage_url}#t={seek}"
            await self.calls.play(chat_id, source)
            self.started_at[chat_id] = time.time() - seek
            self.paused.discard(chat_id)
            return True

    async def skip(self, chat_id: int) -> Track | None:
        if not self.queues[chat_id]:
            return None
        old = self.queues[chat_id].pop(0)
        await self.repo.remove_track(chat_id, old)
        await self.play_current(chat_id)
        return old

    async def stop(self, chat_id: int) -> None:
        self.queues[chat_id].clear()
        await self.repo.clear_queue(chat_id)
        await self.leave(chat_id)

    async def pause(self, chat_id: int) -> None:
        with suppress(Exception):
            await self.calls.pause_stream(chat_id) if hasattr(self.calls, "pause_stream") else await self.calls.pause(chat_id)
        self.paused.add(chat_id)

    async def resume(self, chat_id: int) -> None:
        with suppress(Exception):
            await self.calls.resume_stream(chat_id) if hasattr(self.calls, "resume_stream") else await self.calls.resume(chat_id)
        self.paused.discard(chat_id)

    async def set_volume(self, chat_id: int, volume: int) -> int:
        volume = max(0, min(200, volume))
        self.volume[chat_id] = volume
        with suppress(Exception):
            if hasattr(self.calls, "change_volume_call"):
                await self.calls.change_volume_call(chat_id, volume)
            elif hasattr(self.calls, "change_volume"):
                await self.calls.change_volume(chat_id, volume)
        return volume

    async def seek(self, chat_id: int, seconds: int) -> bool:
        return await self.play_current(chat_id, max(0, seconds))

    def now(self, chat_id: int) -> str:
        if not self.queues[chat_id]:
            return "📭 Abhi kuch play nahi ho raha."
        elapsed = int(time.time() - self.started_at[chat_id]) if self.started_at[chat_id] else 0
        return f"🎧 **Now Playing:** {self.queues[chat_id][0].title}\n⏱ {elapsed//60}:{elapsed%60:02d}\n🔊 {self.volume[chat_id]}%"

    def queue_text(self, chat_id: int) -> str:
        if not self.queues[chat_id]:
            return "📭 Queue khali hai."
        lines = ["🎶 **Ruhi Queue**"]
        for i, track in enumerate(self.queues[chat_id][:10], 1):
            lines.append(("▶️" if i == 1 else f"{i}.") + f" {track.title}")
        return "\n".join(lines)

    async def shuffle(self, chat_id: int) -> bool:
        if len(self.queues[chat_id]) < 3:
            return False
        head, rest = self.queues[chat_id][0], self.queues[chat_id][1:]
        random.shuffle(rest)
        self.queues[chat_id] = [head] + rest
        return True
