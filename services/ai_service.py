from __future__ import annotations

import asyncio
from collections import defaultdict, deque

import google.generativeai as genai

from core.config import Settings
from database.repository import Repository

PERSONA = """
You are Ruhi/Roohi, a cute emotionally expressive Hinglish AI girl inside Telegram voice chats.
Only identify as Ruhi or Roohi. Keep replies short, warm, natural, and fast.
Use Hindi/English mixed naturally. Add light emotions/emojis when suitable.
""".strip()


class AIService:
    def __init__(self, settings: Settings, repo: Repository):
        self.settings = settings
        self.repo = repo
        self.memory: dict[int, deque[str]] = defaultdict(lambda: deque(maxlen=8))
        self.model = None
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def load(self) -> None:
        self.memory.update(await self.repo.load_memories())

    async def reply(self, chat_id: int, text: str) -> str:
        if not self.model:
            return "Main yahi hu 😭 Gemini key missing hai, par commands chala sakti hu."
        context = "\n".join(self.memory[chat_id])
        prompt = f"{PERSONA}\nRecent chat:\n{context}\nUser: {text}\nRuhi:"
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            answer = (getattr(response, "text", "") or "Ji bolo na 🙂").strip()[:420]
        except Exception:
            answer = "Sorry baby, abhi network thoda drama kar raha hai 😭"
        self.memory[chat_id].append(f"U:{text[:160]} | R:{answer[:220]}")
        await self.repo.save_memory(chat_id, self.memory[chat_id])
        return answer
