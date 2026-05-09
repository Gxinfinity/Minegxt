from __future__ import annotations

import re

from music.player import MusicPlayer
from services.ai_service import AIService
from services.search_service import SearchService
from services.tts_service import TTSService
from services.weather_service import WeatherService
from voice.assistant import VoiceAssistant


class IntentRouter:
    def __init__(self, ai: AIService, weather: WeatherService, search: SearchService, tts: TTSService, music: MusicPlayer, voice: VoiceAssistant):
        self.ai = ai
        self.weather = weather
        self.search = search
        self.tts = tts
        self.music = music
        self.voice = voice

    def parse_seconds(self, text: str) -> int:
        if ":" in text:
            total = 0
            for part in text.split(":"):
                total = total * 60 + int(part or 0)
            return total
        match = re.search(r"\d+", text or "")
        return int(match.group()) if match else 0

    async def handle(self, chat_id: int, text: str, speak: bool = True) -> str:
        clean = (text or "").strip()
        low = clean.lower()
        response = ""
        if low.startswith(("play ", "baja ", "bajao ", "gaana ", "song ")) or (" play" in low and "http" in low):
            query = re.sub(r"^(play|baja|bajao|gaana|song)\s+", "", clean, flags=re.I).strip()
            query = re.sub(r"\b(play|baja|bajao|karo|please)\b", "", query, flags=re.I).strip()
            tracks = await self.music.add(chat_id, query)
            response = f"Haan baby, {tracks[0].title} laga diya 🎵" if tracks else "Music nahi mila 😭"
        elif any(x in low for x in ("pause", "ruk", "ruko")):
            await self.music.pause(chat_id); response = "Pause kar diya 🥺"
        elif any(x in low for x in ("resume", "continue", "chalu")):
            await self.music.resume(chat_id); response = "Chalu kar diya ▶️"
        elif any(x in low for x in ("skip", "next", "agla")):
            old = await self.music.skip(chat_id); response = f"Skip kar diya: {old.title}" if old else "Queue khali hai 😭"
        elif any(x in low for x in ("stop", "band", "clear")):
            await self.music.stop(chat_id); response = "Music band kar diya 😭"
        elif low.startswith(("volume ", "awaaz ", "vol ")):
            vol = await self.music.set_volume(chat_id, self.parse_seconds(low)); response = f"Volume {vol}% kar diya 🔊"
        elif low.startswith(("seek ", "forward ", "rewind ")):
            sec = self.parse_seconds(low); await self.music.seek(chat_id, sec); response = "Done baby ⏩"
        elif "weather" in low or "mausam" in low:
            response = await self.weather.weather(clean)
        elif low.startswith(("search ", "google ", "dhundo ")):
            response = await self.search.search(re.sub(r"^(search|google|dhundo)\s+", "", clean, flags=re.I))
        elif "joke" in low or "jokes" in low:
            response = "Ek joke suno: WiFi slow tha, maine bola feelings download ho rahi hain 😭"
        elif "truth" in low:
            response = "Truth: tumhara sabse cute secret kya hai? 🥺"
        elif "dare" in low:
            response = "Dare: ek cute voice note bhejo abhi 😭"
        elif any(x in low for x in ("hello", "hi", "kaisi", "kaha hai")):
            response = "Main yahi hu 😭 bolo kya hua?"
        else:
            response = await self.ai.reply(chat_id, clean)
        if speak:
            await self.voice.speak(chat_id, response)
        return response
