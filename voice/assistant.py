from __future__ import annotations

import asyncio
import logging
import subprocess
import time
import uuid
from contextlib import suppress
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

from core.config import Settings
from music.player import MusicPlayer
from services.tts_service import TTSService

log = logging.getLogger("ruhi.voice")


class VoiceAssistant:
    def __init__(self, settings: Settings, music: MusicPlayer, tts: TTSService):
        self.settings = settings
        self.music = music
        self.tts = tts
        self.whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
        self.buffers: dict[int, list[bytes]] = {}
        self.processing: set[int] = set()
        self.locks: dict[int, asyncio.Lock] = {}
        self.vad_threshold = 700

    def has_wake_word(self, text: str) -> bool:
        clean = text.lower()
        return any(word in clean for word in self.settings.wake_words)

    def strip_wake_word(self, text: str) -> str:
        clean = text
        for word in self.settings.wake_words:
            clean = clean.replace(word, " ").replace(word.title(), " ")
        return " ".join(clean.split())

    async def transcribe_file(self, path: Path) -> str:
        segments, _ = await asyncio.to_thread(self.whisper.transcribe, str(path))
        return " ".join(seg.text for seg in segments).strip()

    async def transcribe_pcm(self, pcm: bytes, chat_id: int) -> str:
        raw = self.settings.temp_dir / f"raw_{chat_id}_{uuid.uuid4().hex}.raw"
        wav = self.settings.temp_dir / f"vc_{chat_id}_{uuid.uuid4().hex}.wav"
        raw.write_bytes(pcm)
        try:
            await asyncio.to_thread(
                subprocess.run,
                ["ffmpeg", "-f", "s16le", "-ar", "48000", "-ac", "1", "-i", str(raw), str(wav), "-y", "-loglevel", "quiet"],
                check=True,
            )
            return await self.transcribe_file(wav)
        finally:
            with suppress(Exception): raw.unlink(missing_ok=True)
            with suppress(Exception): wav.unlink(missing_ok=True)

    async def speak(self, chat_id: int, text: str) -> None:
        lock = self.locks.setdefault(chat_id, asyncio.Lock())
        async with lock:
            resume = bool(self.music.queues[chat_id]) and chat_id not in self.music.paused
            resume_at = int(time.time() - self.music.started_at[chat_id]) if resume and self.music.started_at[chat_id] else 0
            if resume:
                await self.music.pause(chat_id)
            path = await self.tts.synthesize(chat_id, text)
            try:
                await self.music.calls.play(chat_id, str(path))
                await asyncio.sleep(max(2, min(12, len(text.split()) // 2)))
            finally:
                with suppress(Exception): path.unlink(missing_ok=True)
            if resume:
                await self.music.seek(chat_id, resume_at)

    def ingest_raw_frame(self, chat_id: int, frame: bytes) -> bytes | None:
        audio = np.frombuffer(frame, dtype=np.int16)
        if not len(audio):
            return None
        energy = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
        buf = self.buffers.setdefault(chat_id, [])
        if energy > self.vad_threshold:
            buf.append(frame)
            if len(buf) > 260:
                del buf[:80]
            return None
        if len(buf) > 25:
            data = b"".join(buf)
            buf.clear()
            return data
        return None
