from __future__ import annotations

import asyncio
from dataclasses import dataclass
from collections import defaultdict
from contextlib import suppress

import requests
from youtubesearchpython import VideosSearch
from yt_dlp import YoutubeDL


@dataclass
class Track:
    title: str
    url: str
    webpage: str = ""


class MusicPlayer:

    def __init__(self, calls=None, settings=None, repo=None):
        self.calls = calls
        self.settings = settings
        self.repo = repo

        self.queues = defaultdict(list)
        self.active = set()

    async def load(self):
        return True

    async def join(self, chat_id: int):

        if chat_id in self.active:
            return True

        try:

            silent = "https://github.com/anars/blank-audio/raw/master/1-second-of-silence.mp3"

            await self.calls.play(chat_id, silent)

            self.active.add(chat_id)

            print(f"REAL VC JOINED => {chat_id}", flush=True)

            return True

        except Exception as e:

            print(f"VC JOIN ERROR => {e}", flush=True)

            return False

    async def leave(self, chat_id: int):

        try:

            if hasattr(self.calls, "leave_group_call"):
                await self.calls.leave_group_call(chat_id)

            elif hasattr(self.calls, "leave_call"):
                await self.calls.leave_call(chat_id)

        except Exception as e:
            print(f"LEAVE ERROR => {e}", flush=True)

        self.active.discard(chat_id)
        self.queues.pop(chat_id, None)

        return True



    async def resolve(self, query: str):

        print("RESOLVE START", flush=True)

        try:

            results = VideosSearch(f"{query} song", limit=1).result()

            if not results["result"]:
                return []

            video = results["result"][0]

            print(f"VIDEO => {video['title']}", flush=True)

            ydl_opts = {
                "quiet": True,
                "cookiefile": "/root/cookies/youtube.txt",
                "format": "140/bestaudio[ext=m4a]/best",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "noplaylist": True,
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "js_runtimes": {"bun": {}},
                "remote_components": "ejs:github",
                "extractor_args": {
                    "youtube": {
                        "player_client": ["web_creator"],
                        "player_skip": ["web_embedded_web_player"]
                    }
                }
            }

            with YoutubeDL(ydl_opts) as ydl:

                info = await asyncio.to_thread(
                    ydl.extract_info,
                    video["link"],
                    download=True
                )

            if "entries" in info:
                info = info["entries"][0]

            stream = ydl.prepare_filename(info)

            if not stream:
                print("NO FILE 😭", flush=True)
                return []

            print(f"DOWNLOADED => {stream}", flush=True)

            return [
                Track(
                    title=video["title"],
                    url=stream,
                    webpage=video["link"]
                )
            ]

        except Exception as e:

            print(f"SEARCH ERROR => {e}", flush=True)

            return []


    async def add(self, chat_id: int, query: str):

        tracks = await self.resolve(query)

        if not tracks:
            return []

        self.queues[chat_id].extend(tracks)

        await self.join(chat_id)

        try:

            await self.calls.play(chat_id, tracks[0].url)

            print(f"PLAYING => {tracks[0].title}", flush=True)

        except Exception as e:

            print(f"PLAY ERROR => {e}", flush=True)

        return tracks

    async def pause(self, chat_id: int):

        with suppress(Exception):
            await self.calls.pause_stream(chat_id)

    async def resume(self, chat_id: int):

        with suppress(Exception):
            await self.calls.resume_stream(chat_id)

    async def stop(self, chat_id: int):

        self.queues.pop(chat_id, None)

        await self.leave(chat_id)

    async def skip(self, chat_id: int):

        q = self.queues.get(chat_id, [])

        if not q:
            return None

        old = q.pop(0)

        if q:

            try:
                await self.calls.play(chat_id, q[0].url)
            except Exception as e:
                print(f"SKIP ERROR => {e}", flush=True)

        else:
            await self.stop(chat_id)

        return old

    async def seek(self, chat_id: int, sec: int):
        return True