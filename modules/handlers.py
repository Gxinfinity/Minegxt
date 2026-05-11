from __future__ import annotations

import random
import time
from contextlib import suppress
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ai.intent import IntentRouter
from services.tts_service import LANGUAGE_VOICES

TRUTHS = ["Sach sach batao, crush hai kya? 🥺", "Last time jhoot kab bola?", "Sabse embarrassing moment kya tha?"]
DARES = ["Ek cute voice note bhejo 😭", "10 pushups karo ya truth bolo!", "Apna fav song group me batao 🎵"]


class TelegramHandlers:
    def __init__(self, bot: Client, router: IntentRouter):
        self.bot = bot
        self.router = router
        self.quiz_answer: dict[int, str] = {}
        self.cooldown: dict[int, float] = {}

    def register(self) -> None:
        @self.bot.on_message(filters.command(["start", "help", "play", "p", "skip", "stop", "pause", "resume", "queue", "q", "join", "leave", "volume", "vol", "quiz", "truth", "dare", "ttt", "np", "seek", "forward", "rewind", "shuffle", "ask", "search", "weather", "lang"], prefixes=["/", "!", "."]) & filters.incoming)
        async def commands(_, message: Message):
            await self._command(message)

        @self.bot.on_message(filters.voice & filters.incoming)
        async def voice_note(_, message: Message):
            await self._voice_note(message)

        @self.bot.on_callback_query(filters.regex("^(ttt_|qz_)"))
        async def callbacks(_, callback: CallbackQuery):
            await callback.answer("Feature active 🙂", show_alert=False)

    async def _admin_ok(self, message: Message, command: str) -> bool:
        if message.chat.type == ChatType.PRIVATE:
            return True
        if command not in {"play", "p", "skip", "stop", "pause", "resume", "join", "leave", "volume", "vol", "seek", "forward", "rewind", "shuffle"}:
            return True
        member = await self.bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in {ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR}

    async def _command(self, message: Message) -> None:
        cmd = message.command[0].lower()
        if not await self._admin_ok(message, cmd):
            return await message.reply("❌ Sirf admins music/VC control kar sakte hain.")
        chat_id = message.chat.id
        args = " ".join(message.command[1:]).strip()
        if cmd == "start":
            return await message.reply("✨ **Ruhi Supreme AI online hai!**\nCute Hinglish VC assistant ready hu 😭 /help dekho.")
        if cmd == "help":
            return await message.reply("🎀 **Ruhi Commands**\n/play, /skip, /stop, /pause, /resume, /queue, /join, /volume\n/ask, /search, /weather, /quiz, /truth, /dare, /ttt\nVoice: `Ruhi play Kesariya`, `Roohi weather Delhi`")
        if cmd in {"play", "p"}:
            if not args: return await message.reply("🎵 Song name ya link do na.")
            status = await message.reply("🔎 Ruhi search kar rahi hai...")
            added = await self.router.music.add(chat_id, args)
            return await status.edit("❌ Music nahi mila.") if not added else await status.edit("🎵 Added:\n" + "\n".join(f"• {t.title}" for t in added[:5]))
        if cmd == "join":
            await self.router.music.join(chat_id); return await message.reply("🎙 VC join kar liya baby.")
        if cmd == "leave":
            await self.router.music.leave(chat_id); return await message.reply("👋 VC leave kar diya.")
        if cmd == "skip":
            old = await self.router.music.skip(chat_id); return await message.reply(f"⏭ Skipped: {old.title}" if old else "📭 Queue khali hai.")
        if cmd == "stop":
            await self.router.music.stop(chat_id); return await message.reply("⏹ Music band aur queue clear.")
        if cmd == "pause":
            await self.router.music.pause(chat_id); return await message.reply("⏸ Paused.")
        if cmd == "resume":
            await self.router.music.resume(chat_id); return await message.reply("▶️ Resumed.")
        if cmd in {"queue", "q"}: return await message.reply(self.router.music.queue_text(chat_id))
        if cmd == "np": return await message.reply(self.router.music.now(chat_id))
        if cmd in {"volume", "vol"}:
            vol = await self.router.music.set_volume(chat_id, int(args or 100)); return await message.reply(f"🔊 Volume {vol}%")
        if cmd in {"seek", "forward", "rewind"}:
            sec = self.router.parse_seconds(args)
            if cmd == "forward": sec += int(time.time() - self.router.music.started_at[chat_id])
            if cmd == "rewind": sec = max(0, int(time.time() - self.router.music.started_at[chat_id]) - sec)
            ok = await self.router.music.seek(chat_id, sec); return await message.reply("⏩ Done." if ok else "📭 Queue khali hai.")
        if cmd == "shuffle":
            ok = await self.router.music.shuffle(chat_id); return await message.reply("🔀 Shuffled." if ok else "Queue me aur songs chahiye.")
        if cmd == "truth": return await message.reply("🤔 " + random.choice(TRUTHS))
        if cmd == "dare": return await message.reply("🔥 " + random.choice(DARES))
        if cmd == "weather": return await message.reply(await self.router.weather.weather(args))
        if cmd == "search": return await message.reply(await self.router.search.search(args))
        if cmd == "ask": return await message.reply(await self.router.ai.reply(chat_id, args))
        if cmd == "lang":
            ok = self.router.tts.set_language(chat_id, args); return await message.reply("🌐 Voice set." if ok else f"Supported: {', '.join(LANGUAGE_VOICES)}")
        if cmd == "intro":
    return await message.reply(
        """
🔥 **RUHI AI SUPREME** 🔥

🤖 Most Advanced Multi-Feature Telegram Assistant

━━━━━━━━━━━━━━━━━━
⚡ MAIN FEATURES
━━━━━━━━━━━━━━━━━━

🧠 AI Chat Assistant
• Smart AI replies
• Human-like conversation
• Fast response system
• Multi-language support

🎤 Voice Features
• Text To Speech
• Voice Reply
• Multiple Languages
• Smart Voice Processing

📚 Study & Quiz System
• Biology Quiz
• Chemistry Quiz
• Physics Quiz
• Math Quiz
• GK Questions
• AI Explanation System
• Accuracy Tracking
• Subject Wise Tests

🎮 Fun & Games
• TicTacToe
• Truth & Dare
• Random Fun Replies
• Interactive Buttons
• Mini Games

🌦 Utility Commands
• Weather Search
• Google Search
• AI Ask System
• Smart Tools
• Language Changer

🎵 Media Features
• Music Support
• Video Support
• Download System
• Audio Tools

🛡 Advanced System
• Fast Performance
• Inline Buttons
• Callback System
• Async Speed
• Error Handling
• Premium UI

━━━━━━━━━━━━━━━━━━
📖 AVAILABLE COMMANDS
━━━━━━━━━━━━━━━━━━

/ask → AI Chat
/weather → Weather Info
/search → Search Anything
/lang → Change Voice Language
/quiz → Start Quiz
/ttt → TicTacToe
/intro → Bot Introduction

━━━━━━━━━━━━━━━━━━
🚀 RUHI AI SUPREME
Made For Speed • Power • Intelligence
━━━━━━━━━━━━━━━━━━
""",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🧠 AI Chat",
                        callback_data="intro_ai"
                    ),
                    InlineKeyboardButton(
                        "📚 Quiz",
                        callback_data="intro_quiz"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🎮 Games",
                        callback_data="intro_games"
                    ),
                    InlineKeyboardButton(
                        "⚙ Features",
                        callback_data="intro_features"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔥 Ruhi Supreme",
                        callback_data="intro_home"
                    )
                ]
            ]
        )
    )
        if cmd == "xoxo": return await message.reply("🎮 TicTacToe coming alive: use callbacks soon 🙂")

    async def _voice_note(self, message: Message) -> None:
        if not message.from_user:
            return
        status = await message.reply("🎤 Ruhi sun rahi hai...")
        path = Path(await message.download(file_name=f"voice_{message.id}.ogg"))
        try:
            text = await self.router.voice.transcribe_file(path)
            print(f"VOICE TEXT => {text}", flush=True)
            if not self.router.voice.has_wake_word(text):
                return await status.edit("👂 Wake word bolo: Ruhi ya Roohi")
            reply = await self.router.handle(message.chat.id, self.router.voice.strip_wake_word(text), speak=message.chat.id in self.router.music.active)
            await status.edit(reply[:900])
        finally:
            with suppress(Exception): path.unlink(missing_ok=True)
