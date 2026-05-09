from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

import psutil
import uvloop
from pyrogram import Client, idle
from pytgcalls import PyTgCalls

from ai.intent import IntentRouter
from core.config import Settings
from core.logging import setup_logging
from database.repository import Repository
from modules.handlers import TelegramHandlers
from music.player import MusicPlayer
from services.ai_service import AIService
from services.search_service import SearchService
from services.tts_service import TTSService
from services.weather_service import WeatherService
from voice.assistant import VoiceAssistant

log = logging.getLogger("ruhi.app")


class RuhiApplication:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.repo = Repository(settings.database_path)
        self.bot = Client("RuhiBot", api_id=settings.api_id, api_hash=settings.api_hash, bot_token=settings.bot_token)
        self.assistant = Client("RuhiAssistant", api_id=settings.api_id, api_hash=settings.api_hash, session_string=settings.session_string)
        self.calls = PyTgCalls(self.assistant)
        self.music = MusicPlayer(self.calls, settings, self.repo)
        self.tts = TTSService(settings)
        self.ai = AIService(settings, self.repo)
        self.weather = WeatherService(settings)
        self.search = SearchService()
        self.voice = VoiceAssistant(settings, self.music, self.tts)
        self.router = IntentRouter(self.ai, self.weather, self.search, self.tts, self.music, self.voice)
        self.handlers = TelegramHandlers(self.bot, self.router)
        self.tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        self.settings.validate()
        await self.repo.init()
        await self.music.load()
        await self.ai.load()
        self.handlers.register()
        await self.bot.start()
        await self.assistant.start()
        await self.calls.start()
        self.tasks.append(asyncio.create_task(self.watchdog()))
        log.info("Ruhi Supreme AI live. Memory %.1f%%", psutil.virtual_memory().percent)
        await idle()

    async def stop(self) -> None:
        for task in self.tasks:
            task.cancel()
        with suppress(Exception): await self.calls.stop()
        with suppress(Exception): await self.assistant.stop()
        with suppress(Exception): await self.bot.stop()

    async def watchdog(self) -> None:
        while True:
            await asyncio.sleep(30)
            if not getattr(self.assistant, "is_connected", False):
                with suppress(Exception): await self.assistant.connect()
            for chat_id in list(self.music.active):
                if self.music.queues[chat_id]:
                    with suppress(Exception): await self.music.join(chat_id)
            log.info("watchdog ok | active=%s | mem=%.1f%%", len(self.music.active), psutil.virtual_memory().percent)


def run() -> None:
    setup_logging()
    with suppress(Exception):
        uvloop.install()
    app = RuhiApplication(Settings())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(app.stop()))
    try:
        loop.run_until_complete(app.start())
    finally:
        loop.run_until_complete(app.stop())
        loop.close()
