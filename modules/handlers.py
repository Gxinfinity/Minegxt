# =========================================================
# KEEP ONLY THIS AT TOP OF FILE
# =========================================================

from __future__ import annotations

import random
import time
from contextlib import suppress
from pathlib import Path

from pyrogram import Client, filters

from pyrogram.enums import (
    ChatMemberStatus,
    ChatType,
    ButtonStyle
)

from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message
)

from kurigram.types import InlineKeyboardButton

from ai.intent import IntentRouter
from services.tts_service import LANGUAGE_VOICES


# =========================================================
# START BLOCK
# REPLACE ONLY OLD:
# if cmd == "start":
# BLOCK INSIDE _command()
# =========================================================

if cmd == "start":

    START_TEXT = """
✨ **𝗥𝘂𝗵𝗶 𝗦𝘂𝗽𝗿𝗲𝗺𝗲 𝗔𝗜 𝗜𝘀 𝗢𝗻𝗹𝗶𝗻𝗲 💫**

╭━━━━━━━━━━━━━━━╮
┃ 🧠 𝗔𝗜 𝗔𝘀𝘀𝗶𝘀𝘁𝗮𝗻𝘁
┃ 📚 𝗤𝘂𝗶𝘇 𝗦𝘆𝘀𝘁𝗲𝗺
┃ 🎮 𝗙𝘂𝗻 & 𝗚𝗮𝗺𝗲𝘀
┃ 🎵 𝗩𝗖 𝗠𝘂𝘀𝗶𝗰 𝗣𝗹𝗮𝘆𝗲𝗿
┃ 🌦 𝗪𝗲𝗮𝘁𝗵𝗲𝗿
┃ 🎤 𝗩𝗼𝗶𝗰𝗲 𝗔𝗜
╰━━━━━━━━━━━━━━━╯

⚡ 𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗕𝘆 𝗥𝘂𝗵𝗶 𝗦𝘂𝗽𝗿𝗲𝗺𝗲 𝗘𝗻𝗴𝗶𝗻𝗲
🔥 𝗙𝗮𝘀𝘁 • 𝗦𝗺𝗮𝗿𝘁 • 𝗣𝗼𝘄𝗲𝗿𝗳𝘂𝗹

━━━━━━━━━━━━━━━━━━
💡 𝗦𝗲𝗹𝗲𝗰𝘁 𝗔 𝗦𝗲𝗰𝘁𝗶𝗼𝗻 𝗕𝗲𝗹𝗼𝘄
━━━━━━━━━━━━━━━━━━
"""

    START_BUTTONS = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="🧠 𝗔𝗜",
                    callback_data="intro_ai",
                    style=ButtonStyle.PRIMARY
                ),
                InlineKeyboardButton(
                    text="📚 𝗤𝘂𝗶𝘇",
                    callback_data="intro_quiz",
                    style=ButtonStyle.SUCCESS
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎵 𝗠𝘂𝘀𝗶𝗰",
                    callback_data="intro_music",
                    style=ButtonStyle.DANGER
                ),
                InlineKeyboardButton(
                    text="🎮 𝗚𝗮𝗺𝗲𝘀",
                    callback_data="intro_games",
                    style=ButtonStyle.SECONDARY
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚡ 𝗙𝗲𝗮𝘁𝘂𝗿𝗲𝘀",
                    callback_data="intro_features",
                    style=ButtonStyle.PRIMARY
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ 𝗔𝗱𝗱 𝗠𝗲 𝗧𝗼 𝗬𝗼𝘂𝗿 𝗚𝗿𝗼𝘂𝗽",
                    url="https://t.me/YOUR_BOT_USERNAME?startgroup=true",
                    style=ButtonStyle.SUCCESS
                )
            ]
        ]
    )

    return await message.reply_photo(
        photo="https://graph.org/file/2f8e61c55d311070339c8-17b572b5c7c8ad0907.jpg",
        caption=START_TEXT,
        reply_markup=START_BUTTONS
    )


# =========================================================
# INTRO BLOCK
# REPLACE ONLY OLD:
# if cmd == "intro":
# BLOCK INSIDE _command()
# =========================================================

if cmd == "intro":

    INTRO_TEXT = """
🔥 **𝗥𝗨𝗛𝗜 𝗔𝗜 𝗦𝗨𝗣𝗥𝗘𝗠𝗘** 🔥

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
🎵 MUSIC COMMANDS
━━━━━━━━━━━━━━━━━━

/play
/pause
/resume
/skip
/stop
/queue
/join
/leave

━━━━━━━━━━━━━━━━━━
🧠 AI COMMANDS
━━━━━━━━━━━━━━━━━━

/ask
/search
/weather
/lang

━━━━━━━━━━━━━━━━━━
🎮 FUN COMMANDS
━━━━━━━━━━━━━━━━━━

/truth
/dare
/xoxo

━━━━━━━━━━━━━━━━━━
🚀 RUHI SUPREME
━━━━━━━━━━━━━━━━━━
"""

    INTRO_BUTTONS = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="📚 Quiz Hub",
                    callback_data="intro_quiz",
                    style=ButtonStyle.SUCCESS
                ),
                InlineKeyboardButton(
                    text="🧠 AI",
                    callback_data="intro_ai",
                    style=ButtonStyle.PRIMARY
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎮 Games",
                    callback_data="intro_games",
                    style=ButtonStyle.SECONDARY
                ),
                InlineKeyboardButton(
                    text="🎵 Music",
                    callback_data="intro_music",
                    style=ButtonStyle.DANGER
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚡ Features",
                    callback_data="intro_features",
                    style=ButtonStyle.PRIMARY
                )
            ]
        ]
    )

    return await message.reply_photo(
        photo="https://graph.org/file/2f8e61c55d311070339c8-17b572b5c7c8ad0907.jpg",
        caption=INTRO_TEXT,
        reply_markup=INTRO_BUTTONS
    )
# =====================================================
# CALLBACK BUTTONS UI
# =====================================================

@self.bot.on_callback_query(filters.regex("^(ttt_|qz_|intro_)"))
async def callbacks(_, callback: CallbackQuery):

    if callback.data == "intro_ai":

        return await callback.message.edit_caption(
            caption="""
🧠 **RUHI AI COMMANDS**

/ask [question]
➜ AI se kuch bhi pucho

/search [query]
➜ Web search

/weather [city]
➜ Weather check

/lang [language]
➜ Voice language change

━━━━━━━━━━━━━━━━━━
🔥 Smart AI Enabled
━━━━━━━━━━━━━━━━━━
""",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 Back",
                            callback_data="intro_back"
                        )
                    ]
                ]
            )
        )

    elif callback.data == "intro_quiz":

        return await callback.message.edit_caption(
            caption="""
📚 **QUIZ COMMANDS**

/quizhub
/subjects
/test
/pollquiz
/voicequiz
/rapid
/mocktest

/report
/progress
/analysis

━━━━━━━━━━━━━━━━━━
🏆 Competitive Quiz Mode
━━━━━━━━━━━━━━━━━━
""",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 Back",
                            callback_data="intro_back"
                        )
                    ]
                ]
            )
        )

    elif callback.data == "intro_music":

        return await callback.message.edit_caption(
            caption="""
🎵 **MUSIC COMMANDS**

/play
/pause
/resume
/skip
/stop
/queue
/join
/leave

━━━━━━━━━━━━━━━━━━
🎶 High Quality VC Music
━━━━━━━━━━━━━━━━━━
""",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 Back",
                            callback_data="intro_back"
                        )
                    ]
                ]
            )
        )

    elif callback.data == "intro_games":

        return await callback.message.edit_caption(
            caption="""
🎮 **FUN & GAMES**

/truth
/dare
/xoxo

━━━━━━━━━━━━━━━━━━
😂 Multiplayer Fun
━━━━━━━━━━━━━━━━━━
""",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 Back",
                            callback_data="intro_back"
                        )
                    ]
                ]
            )
        )

    elif callback.data == "intro_features":

        return await callback.message.edit_caption(
            caption="""
⚡ **RUHI FEATURES**

✅ AI Chat
✅ Voice AI
✅ Quiz System
✅ Music System
✅ Multiplayer Games
✅ Async Fast Engine
✅ Admin Controls
✅ Competitive Exams

━━━━━━━━━━━━━━━━━━
🔥 Supreme Edition
━━━━━━━━━━━━━━━━━━
""",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 Back",
                            callback_data="intro_back"
                        )
                    ]
                ]
            )
        )

    elif callback.data == "intro_back":

    return await callback.message.edit_caption(
        caption="""
✨ **𝗥𝘂𝗵𝗶 𝗦𝘂𝗽𝗿𝗲𝗺𝗲 𝗔𝗜 💫**

╭━━━━━━━━━━━━━━━╮
┃ 🧠 𝗦𝗺𝗮𝗿𝘁 𝗔𝗜 𝗔𝘀𝘀𝗶𝘀𝘁𝗮𝗻𝘁
┃ 📚 𝗔𝗱𝘃𝗮𝗻𝗰𝗲𝗱 𝗤𝘂𝗶𝘇 𝗦𝘆𝘀𝘁𝗲𝗺
┃ 🎮 𝗙𝘂𝗻 & 𝗠𝘂𝗹𝘁𝗶𝗽𝗹𝗮𝘆𝗲𝗿 𝗚𝗮𝗺𝗲𝘀
┃ 🎵 𝟮𝟰×𝟳 𝗩𝗖 𝗠𝘂𝘀𝗶𝗰
┃ 🌦 𝗟𝗶𝘃𝗲 𝗪𝗲𝗮𝘁𝗵𝗲𝗿
┃ 🎤 𝗩𝗼𝗶𝗰𝗲 𝗔𝗜 𝗦𝘂𝗽𝗽𝗼𝗿𝘁
╰━━━━━━━━━━━━━━━╯

⚡ 𝗙𝗮𝘀𝘁 • 𝗦𝗺𝗮𝗿𝘁 • 𝗣𝗼𝘄𝗲𝗿𝗳𝘂𝗹
🔥 𝗧𝗵𝗲 𝗨𝗹𝘁𝗶𝗺𝗮𝘁𝗲 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗔𝗜 𝗘𝘅𝗽𝗲𝗿𝗶𝗲𝗻𝗰𝗲

━━━━━━━━━━━━━━━━━━
💡 𝗦𝗲𝗹𝗲𝗰𝘁 𝗔 𝗙𝗲𝗮𝘁𝘂𝗿𝗲 𝗕𝗲𝗹𝗼𝘄
━━━━━━━━━━━━━━━━━━
""",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="🧠 𝗔𝗜",
                        callback_data="intro_ai",
                        style=ButtonStyle.PRIMARY
                    ),
                    InlineKeyboardButton(
                        text="📚 𝗤𝘂𝗶𝘇",
                        callback_data="intro_quiz",
                        style=ButtonStyle.SUCCESS
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🎵 𝗠𝘂𝘀𝗶𝗰",
                        callback_data="intro_music",
                        style=ButtonStyle.DANGER
                    ),
                    InlineKeyboardButton(
                        text="🎮 𝗚𝗮𝗺𝗲𝘀",
                        callback_data="intro_games",
                        style=ButtonStyle.SECONDARY
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⚡ 𝗙𝗲𝗮𝘁𝘂𝗿𝗲𝘀",
                        callback_data="intro_features",
                        style=ButtonStyle.PRIMARY
                    )
                ]
            ]
        )
    )

    await callback.answer(
        "🔥 Feature Active",
        show_alert=False
    )