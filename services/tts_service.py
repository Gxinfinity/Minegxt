from __future__ import annotations

import uuid
from pathlib import Path

import edge_tts

from core.config import Settings

LANGUAGE_VOICES = {
    "hi": "hi-IN-SwaraNeural",
    "hinglish": "hi-IN-SwaraNeural",
    "en": "en-IN-NeerjaNeural",
    "english": "en-IN-NeerjaNeural",
    "ur": "ur-PK-UzmaNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "ar": "ar-SA-ZariyahNeural",
}


class TTSService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.chat_voice: dict[int, str] = {}

    def set_language(self, chat_id: int, language: str) -> bool:
        voice = LANGUAGE_VOICES.get(language.lower().strip())
        if not voice:
            return False
        self.chat_voice[chat_id] = voice
        return True

    async def synthesize(self, chat_id: int, text: str) -> Path:
        path = self.settings.temp_dir / f"tts_{uuid.uuid4().hex}.mp3"
        voice = self.chat_voice.get(chat_id, self.settings.default_voice)
        await edge_tts.Communicate(text[:500], voice).save(str(path))
        return path
