from __future__ import annotations

import random
import time
from contextlib import suppress
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message
)

from ai.intent import IntentRouter
from services.tts_service import LANGUAGE_VOICES


# =========================================================
# TRUTH & DARE DATABASE
# =========================================================

TRUTHS = [
    "Sach sach batao, crush hai kya? 🥺",
    "Last time jhoot kab bola?",
    "Sabse embarrassing moment kya tha?",
    "Kabhi kisi ko secretly stalk kiya? 👀",
    "Biggest fear kya hai?",
    "Kisi pe jealous hue ho?",
    "Most toxic thing jo ki?",
    "Phone me weirdest photo kya hai?",
    "Apna hidden talent batao 😭",
    "Kabhi fake cry kiya?"
]

DARES = [
    "Ek cute voice note bhejo 😭",
    "10 pushups karo ya truth bolo!",
    "Apna fav song group me batao 🎵",
    "1 minute caps me baat karo 😂",
    "Gallery ka 5th pic bhejo 👀",
    "Ek shayari likho 😭",
    "Group me kisi ko compliment do 💖",
    "Emoji language me baat karo 😂",
    "Apna wallpaper dikhao 📱",
    "Meme se mood explain karo 😭"
]


# =========================================================
# HANDLER SYSTEM
# =========================================================

class TelegramHandlers:

    def __init__(self, bot: Client, router: IntentRouter):
        self.bot = bot
        self.router = router
        self.quiz_answer: dict[int, str] = {}
        self.cooldown: dict[int, float] = {}

    # =====================================================
    # REGISTER
    # =====================================================

    def register(self) -> None:

        @self.bot.on_message(
            filters.command([
                "start", "help",

                "play", "p",
                "skip",
                "stop",
                "pause",
                "resume",
                "queue", "q",
                "join",
                "leave",
                "volume", "vol",
                "np",
                "seek",
                "forward",
                "rewind",
                "shuffle",

                "ask",
                "search",
                "weather",
                "lang",

                "quiz",
                "quizhub",
                "subjects",
                "pollquiz",
                "voicequiz",
                "dailyquiz",
                "report",
                "leaderboard",
                "profile",
                "rapid",
                "mocktest",

                "streak",
                "rank",
                "accuracy",
                "weakness",
                "improve",
                "history",
                "stats",
                "progress",
                "performance",
                "analysis",

                "neetquiz",
                "jeequiz",
                "upscquiz",
                "sscquiz",
                "gkquiz",
                "pharmacyquiz",
                "engineeringquiz",
                "medicalquiz",
                "commercequiz",
                "lawquiz",
                "psychologyquiz",
                "languagequiz",

                "currentaffairs",
                "randomquiz",
                "topicquiz",
                "chapterquiz",

                "test",
                "startquiz",
                "stopquiz",
                "nextquestion",

                "hint",
                "explain",
                "revision",

                "favorite",
                "bookmark",
                "retrywrong",

                "badges",
                "achievements",

                "competition",
                "challenge",
                "duel",

                "truth",
                "dare",

                "ttt",
                "xoxo",

                "intro"
            ],
            prefixes=["/", "!", "."]
        ) & filters.incoming)

        async def commands(_, message: Message):
            await self._command(message)

        @self.bot.on_message(filters.voice & filters.incoming)
        async def voice_note(_, message: Message):
            await self._voice_note(message)

        @self.bot.on_callback_query(filters.regex("^(ttt_|qz_|intro_)"))
        async def callbacks(_, callback: CallbackQuery):
            await callback.answer("🔥 Feature Active", show_alert=False)

    # =====================================================
    # ADMIN CHECK
    # =====================================================

    async def _admin_ok(
        self,
        message: Message,
        command: str
    ) -> bool:

        if message.chat.type == ChatType.PRIVATE:
            return True

        if command not in {
            "play", "p", "skip",
            "stop", "pause",
            "resume", "join",
            "leave", "volume",
            "vol", "seek",
            "forward", "rewind",
            "shuffle"
        }:
            return True

        member = await self.bot.get_chat_member(
            message.chat.id,
            message.from_user.id
        )

        return member.status in {
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR
        }

    # =====================================================
    # COMMAND HANDLER
    # =====================================================

    async def _command(
        self,
        message: Message
    ) -> None:

        cmd = message.command[0].lower()

        if not await self._admin_ok(message, cmd):
            return await message.reply(
                "❌ Sirf admins VC control kar sakte hain."
            )

        chat_id = message.chat.id
        args = " ".join(message.command[1:]).strip()

        # =================================================
        # BASIC
        # =================================================

        if cmd == "start":

            return await message.reply(
                "✨ **Ruhi Supreme AI Online Hai!**\n\n🧠 AI + 📚 Quiz + 🎮 Games + 🎵 Music"
            )

        if cmd == "help":

            return await message.reply(
                "📚 Use /intro for full feature list."
            )

        # =================================================
        # MUSIC
        # =================================================

        if cmd in {"play", "p"}:

            if not args:
                return await message.reply(
                    "🎵 Song name ya link do."
                )

            status = await message.reply(
                "🔎 Searching..."
            )

            added = await self.router.music.add(
                chat_id,
                args
            )

            if not added:
                return await status.edit(
                    "❌ Song nahi mila."
                )

            return await status.edit(
                "🎵 Added:\n" +
                "\n".join(
                    f"• {t.title}"
                    for t in added[:5]
                )
            )

        if cmd == "join":
            await self.router.music.join(chat_id)
            return await message.reply("🎙 VC joined.")

        if cmd == "leave":
            await self.router.music.leave(chat_id)
            return await message.reply("👋 VC left.")

        if cmd == "skip":
            old = await self.router.music.skip(chat_id)
            return await message.reply(
                f"⏭ Skipped: {old.title}"
                if old else
                "📭 Queue empty."
            )

        if cmd == "stop":
            await self.router.music.stop(chat_id)
            return await message.reply(
                "⏹ Music stopped."
            )

        if cmd == "pause":
            await self.router.music.pause(chat_id)
            return await message.reply("⏸ Paused.")

        if cmd == "resume":
            await self.router.music.resume(chat_id)
            return await message.reply("▶️ Resumed.")

        if cmd in {"queue", "q"}:
            return await message.reply(
                self.router.music.queue_text(chat_id)
            )

        if cmd == "np":
            return await message.reply(
                self.router.music.now(chat_id)
            )

        # =================================================
        # FUN
        # =================================================

        if cmd == "truth":
            return await message.reply(
                "🤔 " + random.choice(TRUTHS)
            )

        if cmd == "dare":
            return await message.reply(
                "🔥 " + random.choice(DARES)
            )

        if cmd == "xoxo":
            return await message.reply(
                "🎮 TicTacToe Coming Soon 🙂"
            )

        # =================================================
        # AI
        # =================================================

        if cmd == "weather":
            return await message.reply(
                await self.router.weather.weather(args)
            )

        if cmd == "search":
            return await message.reply(
                await self.router.search.search(args)
            )

        if cmd == "ask":
            return await message.reply(
                await self.router.ai.reply(chat_id, args)
            )

        if cmd == "lang":

            ok = self.router.tts.set_language(
                chat_id,
                args
            )

            return await message.reply(
                "🌐 Voice changed."
                if ok else
                f"Supported: {', '.join(LANGUAGE_VOICES)}"
            )

        # =================================================
        # INTRO
        # =================================================

        if cmd == "intro":

            return await message.reply(
                """
🔥 **RUHI AI SUPREME** 🔥

🧠 AI Assistant
📚 Quiz System
🎮 Games
🎵 Music
🌦 Weather
🎤 Voice AI
⚡ Fast Async Engine

━━━━━━━━━━━━━━━━━━
📖 QUIZ COMMANDS
━━━━━━━━━━━━━━━━━━

/quizhub
/subjects
/pollquiz Physics
/voicequiz Biology
/test Physics 10
/test Biology 60
/test Chemistry 120

/report
/progress
/accuracy
/weakness
/improve
/analysis
/explain
/hint

/challenge
/competition
/duel
/leaderboard

━━━━━━━━━━━━━━━━━━
🚀 RUHI SUPREME
━━━━━━━━━━━━━━━━━━
                """,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📚 Quiz Hub",
                                callback_data="intro_quiz"
                            ),
                            InlineKeyboardButton(
                                "🧠 AI",
                                callback_data="intro_ai"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "🎮 Games",
                                callback_data="intro_games"
                            ),
                            InlineKeyboardButton(
                                "⚡ Features",
                                callback_data="intro_features"
                            )
                        ]
                    ]
                )
            )

    # =====================================================
    # VOICE NOTE
    # =====================================================

    async def _voice_note(
        self,
        message: Message
    ) -> None:

        if not message.from_user:
            return

        status = await message.reply(
            "🎤 Ruhi sun rahi hai..."
        )

        path = Path(
            await message.download(
                file_name=f"voice_{message.id}.ogg"
            )
        )

        try:

            text = await self.router.voice.transcribe_file(path)

            print(
                f"VOICE TEXT => {text}",
                flush=True
            )

            if not self.router.voice.has_wake_word(text):

                return await status.edit(
                    "👂 Wake word bolo: Ruhi ya Roohi"
                )

            reply = await self.router.handle(
                message.chat.id,
                self.router.voice.strip_wake_word(text),
                speak=message.chat.id in self.router.music.active
            )

            await status.edit(reply[:900])

        finally:

            with suppress(Exception):
                path.unlink(missing_ok=True)