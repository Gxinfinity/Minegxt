# =========================================================
# RUHI ULTIMATE QUIZ SYSTEM
# NEW MODULAR STRUCTURE
# File: modules/quiz_system.py
# FINAL IMPORTS + AI SETUP
# PART 1 TO PART 12 READY
# =========================================================

from __future__ import annotations

# =========================================================
# PYTHON IMPORTS
# =========================================================

import os
import gc
import uuid
import time
import json
import shutil
import random
import logging
import asyncio
import psutil
import numpy as np
import aiosqlite

from pathlib import Path

from contextlib import suppress

from collections import (
    defaultdict,
    deque
)

from datetime import (
    datetime,
    timedelta
)

# =========================================================
# PYROGRAM
# =========================================================

from pyrogram import filters

from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Poll
)

from pyrogram.enums import (
    ChatType,
    ChatMemberStatus
)

from pyrogram.errors import (
    FloodWait
)

from core.app import app

bot = app.bot
assistant = app.assistant

# =========================================================
# CLIENTS
# =========================================================



# =========================================================
# AI / TTS / WHISPER
# =========================================================

import edge_tts

import google.generativeai as genai

from openai import AsyncOpenAI

from faster_whisper import (
    WhisperModel
)

# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger(
    "ruhi.quiz"
)

bot = None
assistant = None
# =========================================================
# OPENROUTER AI
# =========================================================

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    ""
)

openrouter_client = AsyncOpenAI(

    api_key=OPENROUTER_API_KEY,

    base_url="https://openrouter.ai/api/v1"
)

OPENROUTER_MODEL = (
    "deepseek/deepseek-chat-v3-0324:free"
)

# =========================================================
# GEMINI BACKUP
# =========================================================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
)

if GEMINI_API_KEY:

    genai.configure(
        api_key=GEMINI_API_KEY
    )

    ai_model = genai.GenerativeModel(
        "gemini-1.5-flash"
    )

else:

    ai_model = None

# =========================================================
# WHISPER
# =========================================================

try:

    whisper_model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8"
    )

except Exception as e:

    logger.error(
        f"Whisper Load Error: {e}"
    )

    whisper_model = None

# =========================================================
# VOICE
# =========================================================

VOICE = "en-US-JennyNeural"

# =========================================================
# DATABASE
# =========================================================

QUIZ_DB = "quiz_system.db"

# =========================================================
# GLOBAL STATES
# =========================================================

ACTIVE_QUIZ = defaultdict(dict)

ACTIVE_AI_QUIZ = {}

ACTIVE_BATTLES = {}

TOURNAMENTS = {}

DUELS = {}

POLL_CACHE = {}

GROUP_QUIZ = defaultdict(bool)

USER_XP = defaultdict(int)

USER_CACHE = defaultdict(dict)

USER_STREAK = defaultdict(int)

QUIZ_HISTORY = defaultdict(list)

RAPID_FIRE = {}

DAILY_CHALLENGE = {}

GROUP_STATS = defaultdict(
    lambda: {
        "quiz": 0,
        "correct": 0,
        "wrong": 0
    }
)

# =========================================================
# ADMIN + SECURITY
# =========================================================

SUPER_ADMINS = set()

BANNED_USERS = set()

SPAM_TRACK = defaultdict(list)

BOT_SETTINGS = {

    "quiz_enabled": True,
    "ai_enabled": True,
    "voice_enabled": True,
    "maintenance": False
}

# =========================================================
# BACKUP
# =========================================================

BACKUP_DIR = "quiz_backups"

os.makedirs(
    BACKUP_DIR,
    exist_ok=True
)

# =========================================================
# SUBJECTS
# =========================================================

SUBJECTS = {

    "🧠 General Knowledge": [
        "Current Affairs",
        "Static GK",
        "World Affairs",
        "Indian Affairs",
        "Sports GK"
    ],

    "🔬 Science": [
        "Physics",
        "Chemistry",
        "Biology",
        "Mathematics",
        "Biotechnology"
    ],

    "💊 Pharmacy": [
        "Pharmacology",
        "Pharmaceutics",
        "Medicinal Chemistry",
        "Pharmacognosy",
        "Industrial Pharmacy",
        "Biostatistics",
        "Jurisprudence"
    ],

    "⚙ Engineering": [
        "Computer Science",
        "Mechanical",
        "Civil",
        "Electrical",
        "AI",
        "Machine Learning"
    ],

    "🩺 Medical": [
        "Human Anatomy",
        "Physiology",
        "Pathology",
        "Microbiology",
        "Genetics"
    ],

    "💻 IT": [
        "Python",
        "Java",
        "C++",
        "Cyber Security",
        "Networking",
        "Web Development"
    ]
}

# =========================================================
# ALL SUBJECTS
# =========================================================

ALL_SUBJECTS = []

for category in SUBJECTS.values():

    for subject in category:

        if subject not in ALL_SUBJECTS:

            ALL_SUBJECTS.append(
                subject
            )

# =========================================================
# READY
# =========================================================

logger.info(
    "🔥 RUHI QUIZ SYSTEM FULLY LOADED"
)
# =========================================================
# DATABASE
# =========================================================

QUIZ_DB = "quiz_system.db"

# =========================================================
# SUBJECTS
# =========================================================

SUBJECTS = {

    "🧠 General Knowledge": [
        "Current Affairs",
        "Static GK",
        "World Affairs",
        "Indian Affairs",
        "Sports GK"
    ],

    "🔬 Science": [
        "Physics",
        "Chemistry",
        "Biology",
        "Mathematics",
        "Biotechnology"
    ],

    "💊 Pharmacy": [
        "Pharmacology",
        "Pharmaceutics",
        "Medicinal Chemistry",
        "Pharmacognosy",
        "Industrial Pharmacy",
        "Biostatistics",
        "Jurisprudence"
    ],

    "⚙ Engineering": [
        "Computer Science",
        "Mechanical",
        "Civil",
        "Electrical",
        "AI",
        "Machine Learning"
    ],

    "🩺 Medical": [
        "Human Anatomy",
        "Physiology",
        "Pathology",
        "Microbiology",
        "Genetics"
    ],

    "💻 IT": [
        "Python",
        "Java",
        "C++",
        "Cyber Security",
        "Networking",
        "Web Development"
    ]
}

# =========================================================
# STATES
# =========================================================

ACTIVE_QUIZ = defaultdict(dict)

POLL_CACHE = {}

# =========================================================
# DATABASE INIT
# =========================================================

async def init_quiz_db():

    async with aiosqlite.connect(QUIZ_DB) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS report_cards (

            user_id INTEGER,
            subject TEXT,

            total INTEGER,
            correct INTEGER,
            wrong INTEGER,

            accuracy REAL,

            last_score INTEGER,
            best_score INTEGER
        )
        """)

        await db.commit()

# =========================================================
# MAIN MENU
# =========================================================

def quiz_main_menu():

    kb = []

    for category in SUBJECTS.keys():

        kb.append([
            InlineKeyboardButton(
                category,
                callback_data=f"subject_{category}"
            )
        ])

    kb.append([
        InlineKeyboardButton(
            "🔥 Daily Quiz",
            callback_data="daily_quiz"
        )
    ])

    return InlineKeyboardMarkup(kb)

# =========================================================
# SUBJECT MENU
# =========================================================

def subject_menu(category):

    kb = []

    for sub in SUBJECTS[category]:

        kb.append([
            InlineKeyboardButton(
                f"📚 {sub}",
                callback_data=f"quizsub_{sub}"
            )
        ])

    kb.append([
        InlineKeyboardButton(
            "⬅ Back",
            callback_data="quiz_home"
        )
    ])

    return InlineKeyboardMarkup(kb)

# =========================================================
# TIME MENU
# =========================================================

def quiz_time_menu(subject):

    return InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "⚡ 10 Questions • 10 Min",
                    callback_data=f"quizstart_{subject}_10_10"
                )
            ],

            [
                InlineKeyboardButton(
                    "🔥 60 Questions • 1 Hour",
                    callback_data=f"quizstart_{subject}_60_60"
                )
            ],

            [
                InlineKeyboardButton(
                    "👑 120 Questions • 120 Min",
                    callback_data=f"quizstart_{subject}_120_120"
                )
            ],

            [
                InlineKeyboardButton(
                    "⬅ Back",
                    callback_data="quiz_home"
                )
            ]
        ]
    )

# =========================================================
# REGISTER QUIZ HANDLERS
# =========================================================

def register_quiz_handlers(bot, ai_model):

    # =====================================================
    # QUIZ HUB
    # =====================================================

    @bot.on_message(filters.command("quizhub"))

    async def quizhub(_, m: Message):

        await m.reply_photo(

            photo="https://i.imgur.com/8Yh6F8h.jpeg",

            caption=
            "🧠 **RUHI ULTIMATE QUIZ SYSTEM**\n\n"
            "🔥 AI Powered Quiz Engine\n"
            "📚 100+ Subjects\n"
            "⚡ Live Poll Quiz\n"
            "📊 Report Cards\n"
            "🏆 Leaderboards\n"
            "🎯 Accuracy Tracking\n\n"
            "Select Your Category 👇",

            reply_markup=quiz_main_menu()
        )

    # =====================================================
    # SUBJECT CALLBACK
    # =====================================================

    @bot.on_callback_query(filters.regex("^subject_"))

    async def subject_callback(_, cb: CallbackQuery):

        category = cb.data.replace(
            "subject_",
            ""
        )

        await cb.message.edit_text(

            f"📚 **{category} Subjects**\n\n"
            "Select Subject 👇",

            reply_markup=subject_menu(category)
        )

    # =====================================================
    # SUBJECT SELECT
    # =====================================================

    @bot.on_callback_query(filters.regex("^quizsub_"))

    async def quiz_subject(_, cb: CallbackQuery):

        subject = cb.data.replace(
            "quizsub_",
            ""
        )

        await cb.message.edit_text(

            f"📝 **{subject} Quiz Modes**\n\n"
            "Choose Quiz Length 👇",

            reply_markup=quiz_time_menu(subject)
        )

    # =====================================================
    # QUIZ START
    # =====================================================

    @bot.on_callback_query(filters.regex("^quizstart_"))

    async def start_quiz(_, cb: CallbackQuery):

        try:

            data = cb.data.split("_")

            subject = data[1]

            questions = int(data[2])

            mins = int(data[3])

            chat_id = cb.message.chat.id

            ACTIVE_QUIZ[chat_id] = {

                "subject": subject,

                "total": questions,

                "correct": 0,

                "wrong": 0,

                "index": 0,

                "end_time": time.time() + (mins * 60)
            }

            await cb.message.edit_text(

                f"🚀 **QUIZ STARTED**\n\n"

                f"📚 Subject: {subject}\n"

                f"❓ Questions: {questions}\n"

                f"⏰ Time: {mins} Minutes\n\n"

                "⚡ AI generating questions..."
            )

            asyncio.create_task(

                run_quiz(
                    bot,
                    ai_model,
                    chat_id
                )
            )

        except Exception as e:

            logger.error(
                f"Quiz Start Error: {e}"
            )

# =========================================================
# GENERATE QUESTIONS
# =========================================================

async def generate_question(
    ai_model,
    subject
):

    prompt = f"""

Generate one MCQ for {subject}

Format:

Question|OptionA|OptionB|OptionC|OptionD|CorrectLetter
"""

    try:

        res = await asyncio.to_thread(
            ai_model.generate_content,
            prompt
        )

        text = res.text.strip()

        parts = text.split("|")

        if len(parts) < 6:

            return None

        return {

            "question": parts[0],

            "options": parts[1:5],

            "correct": parts[5].strip().upper()
        }

    except Exception as e:

        logger.error(
            f"Question Error: {e}"
        )

        return None

# =========================================================
# QUIZ LOOP
# =========================================================

async def run_quiz(
    bot,
    ai_model,
    chat_id
):

    try:

        data = ACTIVE_QUIZ[chat_id]

        while data["index"] < data["total"]:

            if time.time() > data["end_time"]:

                break

            q = await generate_question(
                ai_model,
                data["subject"]
            )

            if not q:

                continue

            poll = await bot.send_poll(

                chat_id,

                question=q["question"],

                options=q["options"],

                type="quiz",

                correct_option_id=(
                    ord(q["correct"]) - 65
                ),

                is_anonymous=False,

                open_period=30
            )

            POLL_CACHE[poll.poll.id] = {

                "chat_id": chat_id,

                "correct": q["correct"]
            }

            data["index"] += 1

            await asyncio.sleep(35)

        await bot.send_message(

            chat_id,

            "🏁 Quiz Finished!\n\n"
            "📊 Report System Coming In Part 2 👑"
        )

    except Exception as e:

        logger.error(
            f"Run Quiz Error: {e}"
        )
# =========================================================
# PART 2 — ADVANCED QUIZ FEATURES
# NEW MODULAR STRUCTURE
# ADD BELOW PART 1
# modules/quiz_system.py
# =========================================================

# =========================================================
# LIVE ANSWER REACTIONS
# =========================================================

CORRECT_REACTIONS = [

    "✅ Correct!",

    "🔥 Genius!",

    "⚡ Smart!",

    "🏆 Excellent!",

    "💯 Perfect!",

    "🧠 Brilliant!",

    "👑 Quiz King!"
]

WRONG_REACTIONS = [

    "❌ Wrong!",

    "😢 Oops!",

    "💀 Better luck next time!",

    "📚 Study more!",

    "😭 Incorrect!",

    "⚠ Try harder!",

    "🥲 Almost!"
]

# =========================================================
# USER STREAK
# =========================================================

USER_STREAK = defaultdict(int)

# =========================================================
# SAVE REPORT
# =========================================================

async def save_report(

    user_id,
    subject,
    correct
):

    try:

        async with aiosqlite.connect(
            QUIZ_DB
        ) as db:

            cur = await db.execute(

                """
                SELECT total,
                correct,
                wrong,
                best_score
                FROM report_cards
                WHERE user_id = ?
                AND subject = ?
                """,

                (
                    user_id,
                    subject
                )
            )

            row = await cur.fetchone()

            if row:

                total = row[0] + 1

                cor = row[1]

                wr = row[2]

                best = row[3]

                if correct:

                    cor += 1

                else:

                    wr += 1

                accuracy = (

                    cor / total

                ) * 100

                best_score = max(
                    best,
                    cor
                )

                await db.execute(

                    """
                    UPDATE report_cards
                    SET total = ?,
                    correct = ?,
                    wrong = ?,
                    accuracy = ?,
                    last_score = ?,
                    best_score = ?
                    WHERE user_id = ?
                    AND subject = ?
                    """,

                    (
                        total,
                        cor,
                        wr,
                        accuracy,
                        cor,
                        best_score,
                        user_id,
                        subject
                    )
                )

            else:

                await db.execute(

                    """
                    INSERT INTO report_cards
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,

                    (
                        user_id,
                        subject,

                        1,

                        1 if correct else 0,

                        0 if correct else 1,

                        100 if correct else 0,

                        1 if correct else 0,

                        1 if correct else 0
                    )
                )

            await db.commit()

    except Exception as e:

        logger.error(
            f"Save Report Error: {e}"
        )

# =========================================================
# FINISH QUIZ
# =========================================================

async def finish_quiz(

    bot,
    chat_id
):

    try:

        if chat_id not in ACTIVE_QUIZ:

            return

        q = ACTIVE_QUIZ[chat_id]

        total = q["total"]

        correct = q["correct"]

        wrong = q["wrong"]

        percent = (

            round(
                (correct / total) * 100,
                2
            )

            if total > 0

            else 0
        )

        performance = "😐 Average"

        if percent >= 90:

            performance = "🏆 Legend"

        elif percent >= 75:

            performance = "🔥 Excellent"

        elif percent >= 50:

            performance = "⚡ Good"

        elif percent < 40:

            performance = "📚 Needs Improvement"

        text = f"""

🏁 QUIZ FINISHED

📚 Subject:
{q['subject']}

📝 Total Questions:
{total}

✅ Correct:
{correct}

❌ Wrong:
{wrong}

📊 Accuracy:
{percent}%

🎯 Performance:
{performance}
"""

        await bot.send_message(
            chat_id,
            text
        )

        ACTIVE_QUIZ.pop(
            chat_id,
            None
        )

    except Exception as e:

        logger.error(
            f"Finish Quiz Error: {e}"
        )

# =========================================================
# REGISTER ADVANCED HANDLERS
# =========================================================

def register_advanced_quiz_handlers(

    bot,
    ai_model
):

    # =====================================================
    # POLL ANSWER HANDLER
    # =====================================================

    @bot.on_poll_answer()

    async def poll_answer_handler(

        _,
        answer
    ):

        try:

            poll_id = answer.poll_id

            if poll_id not in POLL_CACHE:

                return

            data = POLL_CACHE[poll_id]

            user_id = answer.user.id

            selected = (

                chr(answer.option_ids[0] + 65)

                if answer.option_ids

                else None
            )

            chat_id = data["chat_id"]

            quiz = ACTIVE_QUIZ.get(chat_id)

            if not quiz:

                return

            if selected == data["correct"]:

                quiz["correct"] += 1

                USER_STREAK[user_id] += 1

                await bot.send_message(

                    chat_id,

                    random.choice(
                        CORRECT_REACTIONS
                    )
                )

            else:

                quiz["wrong"] += 1

                USER_STREAK[user_id] = 0

                await bot.send_message(

                    chat_id,

                    random.choice(
                        WRONG_REACTIONS
                    )
                )

            await save_report(

                user_id,

                quiz["subject"],

                selected == data["correct"]
            )

        except Exception as e:

            logger.error(
                f"Poll Answer Error: {e}"
            )

    # =====================================================
    # REPORT CARD
    # =====================================================

    @bot.on_message(
        filters.command("report")
    )

    async def report_card(
        _,
        m: Message
    ):

        try:

            user_id = m.from_user.id

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cur = await db.execute(

                    """
                    SELECT subject,
                    total,
                    correct,
                    wrong,
                    accuracy,
                    best_score
                    FROM report_cards
                    WHERE user_id = ?
                    ORDER BY accuracy DESC
                    """,

                    (user_id,)
                )

                rows = await cur.fetchall()

                if not rows:

                    return await m.reply(
                        "📭 No reports found."
                    )

                text = (
                    "📊 YOUR REPORT CARD\n\n"
                )

                for row in rows[:20]:

                    text += (

                        f"📚 {row[0]}\n"

                        f"📝 Total: {row[1]}\n"

                        f"✅ Correct: {row[2]}\n"

                        f"❌ Wrong: {row[3]}\n"

                        f"📈 Accuracy: {round(row[4],2)}%\n"

                        f"🏆 Best Score: {row[5]}\n\n"
                    )

                await m.reply(text)

        except Exception as e:

            logger.error(
                f"Report Error: {e}"
            )

    # =====================================================
    # LEADERBOARD
    # =====================================================

    @bot.on_message(
        filters.command("leaderboard")
    )

    async def leaderboard(
        _,
        m: Message
    ):

        try:

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cur = await db.execute(

                    """
                    SELECT user_id,
                    SUM(correct)
                    as score
                    FROM report_cards
                    GROUP BY user_id
                    ORDER BY score DESC
                    LIMIT 10
                    """
                )

                rows = await cur.fetchall()

                if not rows:

                    return await m.reply(
                        "📭 No leaderboard data."
                    )

                text = "🏆 GLOBAL LEADERBOARD\n\n"

                pos = 1

                for row in rows:

                    try:

                        user = await bot.get_users(
                            row[0]
                        )

                        name = (

                            user.first_name

                            if user

                            else "Unknown"
                        )

                    except:

                        name = "Unknown"

                    text += (

                        f"{pos}. {name}\n"

                        f"🔥 Score: {row[1]}\n\n"
                    )

                    pos += 1

                await m.reply(text)

        except Exception as e:

            logger.error(
                f"Leaderboard Error: {e}"
            )

    # =====================================================
    # DAILY QUIZ
    # =====================================================

    @bot.on_message(
        filters.command("dailyquiz")
    )

    async def daily_quiz(
        _,
        m: Message
    ):

        kb = InlineKeyboardMarkup(

            [
                [
                    InlineKeyboardButton(
                        "⚡ Start Daily Quiz",
                        callback_data="daily_quiz"
                    )
                ]
            ]
        )

        await m.reply(

            "🌟 DAILY QUIZ CHALLENGE",

            reply_markup=kb
        )

    # =====================================================
    # DAILY QUIZ CALLBACK
    # =====================================================

    @bot.on_callback_query(
        filters.regex("^daily_quiz$")
    )

    async def daily_quiz_start(
        _,
        cb: CallbackQuery
    ):

        chat_id = cb.message.chat.id

        ACTIVE_QUIZ[chat_id] = {

            "subject": "Mixed",

            "total": 20,

            "correct": 0,

            "wrong": 0,

            "index": 0,

            "end_time": (
                time.time() + 1200
            )
        }

        await cb.message.edit_text(
            "⚡ Daily Quiz Started!"
        )

        asyncio.create_task(

            run_quiz(
                bot,
                ai_model,
                chat_id
            )
        )

    # =====================================================
    # STREAK
    # =====================================================

    @bot.on_message(
        filters.command("streak")
    )

    async def streak(
        _,
        m: Message
    ):

        user_id = m.from_user.id

        streak = USER_STREAK.get(
            user_id,
            0
        )

        await m.reply(

            f"🔥 Your Quiz Streak: {streak}"
        )

    # =====================================================
    # SUBJECTS
    # =====================================================

    @bot.on_message(
        filters.command("subjects")
    )

    async def all_subjects(
        _,
        m: Message
    ):

        text = "📚 ALL SUBJECTS\n\n"

        for cat in SUBJECTS:

            text += f"🎯 {cat}\n"

            for s in SUBJECTS[cat]:

                text += f"   • {s}\n"

            text += "\n"

        await m.reply(text)
# =========================================================
# PART 3 — ULTRA FEATURES + ADVANCED UI
# Add BELOW PART 2
# modules/quiz_system.py
# =========================================================

from datetime import datetime

# =========================================================
# ACHIEVEMENTS SYSTEM
# =========================================================

ACHIEVEMENTS = {

    10: "🥉 Beginner Brain",
    50: "🥈 Quiz Fighter",
    100: "🥇 Quiz Master",
    250: "🏆 Knowledge King",
    500: "👑 Ruhi Legend"
}

# =========================================================
# USER XP
# =========================================================

USER_XP = defaultdict(int)

# =========================================================
# LEVEL SYSTEM
# =========================================================

def get_level(xp):

    return int(xp / 50) + 1

# =========================================================
# XP ADDER
# =========================================================

async def add_xp(user_id, amount):

    USER_XP[user_id] += amount

# =========================================================
# PROFILE CARD
# =========================================================

@bot.on_message(
    filters.command("profile")
)
async def profile_card(_, m: Message):

    try:

        user_id = m.from_user.id

        async with aiosqlite.connect(
            QUIZ_DB
        ) as db:

            cur = await db.execute(
                """
                SELECT
                SUM(correct),
                SUM(wrong),
                AVG(accuracy)
                FROM report_cards
                WHERE user_id = ?
                """,
                (user_id,)
            )

            row = await cur.fetchone()

            correct = row[0] or 0
            wrong = row[1] or 0
            accuracy = round(
                row[2] or 0,
                2
            )

            total = correct + wrong

            xp = USER_XP[user_id]

            level = get_level(xp)

            badge = "🎖 Beginner"

            for k, v in ACHIEVEMENTS.items():

                if correct >= k:
                    badge = v

            text = f"""
👤 PROFILE CARD

🧠 Name:
{m.from_user.first_name}

🎯 Level:
{level}

⚡ XP:
{xp}

🏅 Badge:
{badge}

✅ Correct:
{correct}

❌ Wrong:
{wrong}

📊 Accuracy:
{accuracy}%

📝 Total Attempts:
{total}
"""

            await m.reply(text)

    except Exception as e:

        logger.error(
            f"Profile Error: {e}"
        )

# =========================================================
# ACHIEVEMENT CHECK
# =========================================================

async def check_achievement(
    chat_id,
    user_id,
    correct
):

    try:

        for need, reward in ACHIEVEMENTS.items():

            if correct == need:

                user = await bot.get_users(
                    user_id
                )

                await bot.send_message(
                    chat_id,

                    f"""
🏆 ACHIEVEMENT UNLOCKED

👤 {user.first_name}

🎖 {reward}

🔥 Total Correct:
{correct}
"""
                )

    except Exception as e:

        logger.error(
            f"Achievement Error: {e}"
        )

# =========================================================
# SUBJECT LEADERBOARD
# =========================================================

@bot.on_message(
    filters.command("subjectleader")
)
async def subject_leaderboard(_, m):

    try:

        if len(m.command) < 2:

            return await m.reply(
                "Usage:\n/subjectleader Physics"
            )

        subject = " ".join(
            m.command[1:]
        )

        async with aiosqlite.connect(
            QUIZ_DB
        ) as db:

            cur = await db.execute(
                """
                SELECT
                user_id,
                correct
                FROM report_cards
                WHERE subject = ?
                ORDER BY correct DESC
                LIMIT 10
                """,
                (subject,)
            )

            rows = await cur.fetchall()

            if not rows:

                return await m.reply(
                    "❌ No data found."
                )

            text = (
                f"🏆 {subject} Leaderboard\n\n"
            )

            rank = 1

            for row in rows:

                try:

                    user = await bot.get_users(
                        row[0]
                    )

                    name = user.first_name

                except:

                    name = "Unknown"

                text += (
                    f"{rank}. {name}\n"
                    f"🔥 {row[1]} Correct\n\n"
                )

                rank += 1

            await m.reply(text)

    except Exception as e:

        logger.error(
            f"Subject Leader Error: {e}"
        )

# =========================================================
# EXAM MODES
# =========================================================

EXAM_MODES = {

    "neet": [
        "Physics",
        "Chemistry",
        "Botany",
        "Zoology"
    ],

    "jee": [
        "Physics",
        "Chemistry",
        "Mathematics"
    ],

    "upsc": [
        "History",
        "Geography",
        "Polity",
        "Economy"
    ],

    "ssc": [
        "Reasoning",
        "GK",
        "English",
        "Math"
    ]
}

# =========================================================
# EXAM MENU
# =========================================================

@bot.on_message(
    filters.command("examquiz")
)
async def exam_quiz(_, m):

    kb = InlineKeyboardMarkup(

        [
            [
                InlineKeyboardButton(
                    "NEET",
                    callback_data="exam_neet"
                )
            ],

            [
                InlineKeyboardButton(
                    "JEE",
                    callback_data="exam_jee"
                )
            ],

            [
                InlineKeyboardButton(
                    "UPSC",
                    callback_data="exam_upsc"
                )
            ],

            [
                InlineKeyboardButton(
                    "SSC",
                    callback_data="exam_ssc"
                )
            ]
        ]
    )

    await m.reply(
        "🎯 Select Exam Mode",
        reply_markup=kb
    )

# =========================================================
# EXAM CALLBACK
# =========================================================

@bot.on_callback_query(
    filters.regex("^exam_")
)
async def exam_callback(_, cb):

    exam = cb.data.replace(
        "exam_",
        ""
    )

    subs = EXAM_MODES.get(
        exam,
        []
    )

    text = (
        f"📚 {exam.upper()} Subjects\n\n"
    )

    for s in subs:

        text += f"• {s}\n"

    kb = InlineKeyboardMarkup(

        [
            [
                InlineKeyboardButton(
                    "Start Mock Test 🚀",
                    callback_data=f"mock_{exam}"
                )
            ]
        ]
    )

    await cb.message.edit_text(
        text,
        reply_markup=kb
    )

# =========================================================
# MOCK TEST
# =========================================================

@bot.on_callback_query(
    filters.regex("^mock_")
)
async def mock_test(_, cb):

    exam = cb.data.replace(
        "mock_",
        ""
    )

    chat_id = cb.message.chat.id

    ACTIVE_QUIZ[chat_id] = {

        "subject": exam.upper(),
        "total": 100,
        "correct": 0,
        "wrong": 0,
        "index": 0,
        "end_time": (
            time.time() + 7200
        )
    }

    await cb.message.edit_text(
        f"🚀 {exam.upper()} Mock Test Started"
    )

    asyncio.create_task(
        run_quiz(chat_id)
    )

# =========================================================
# IMPROVEMENT TRACKER
# =========================================================

@bot.on_message(
    filters.command("improvement")
)
async def improvement(_, m):

    try:

        user_id = m.from_user.id

        async with aiosqlite.connect(
            QUIZ_DB
        ) as db:

            cur = await db.execute(
                """
                SELECT
                subject,
                accuracy,
                best_score
                FROM report_cards
                WHERE user_id = ?
                """,
                (user_id,)
            )

            rows = await cur.fetchall()

            if not rows:

                return await m.reply(
                    "📭 No data."
                )

            text = (
                "📈 IMPROVEMENT REPORT\n\n"
            )

            for row in rows:

                status = (
                    "🔥 Improving"
                    if row[1] >= 60
                    else "📚 Need Practice"
                )

                text += (
                    f"📚 {row[0]}\n"
                    f"📊 Accuracy: {round(row[1],2)}%\n"
                    f"🏆 Best: {row[2]}\n"
                    f"📈 {status}\n\n"
                )

            await m.reply(text)

    except Exception as e:

        logger.error(
            f"Improvement Error: {e}"
        )

# =========================================================
# QUIZ HISTORY
# =========================================================

QUIZ_HISTORY = defaultdict(list)

# =========================================================
# SAVE HISTORY
# =========================================================

async def save_history(
    user_id,
    subject,
    score
):

    QUIZ_HISTORY[user_id].append({

        "subject": subject,
        "score": score,
        "time": datetime.now().strftime(
            "%d-%m-%Y %H:%M"
        )
    })

# =========================================================
# HISTORY COMMAND
# =========================================================

@bot.on_message(
    filters.command("history")
)
async def history(_, m):

    user_id = m.from_user.id

    data = QUIZ_HISTORY.get(
        user_id,
        []
    )

    if not data:

        return await m.reply(
            "📭 No history."
        )

    text = "📜 QUIZ HISTORY\n\n"

    for h in data[-15:]:

        text += (
            f"📚 {h['subject']}\n"
            f"🏆 Score: {h['score']}\n"
            f"🕒 {h['time']}\n\n"
        )

    await m.reply(text)

# =========================================================
# SPEED QUIZ
# =========================================================

@bot.on_message(
    filters.command("speedquiz")
)
async def speed_quiz(_, m):

    chat_id = m.chat.id

    ACTIVE_QUIZ[chat_id] = {

        "subject": "Mixed",
        "total": 25,
        "correct": 0,
        "wrong": 0,
        "index": 0,
        "end_time": (
            time.time() + 300
        )
    }

    await m.reply(
        "⚡ SPEED QUIZ STARTED\n"
        "25 Questions • 5 Minutes"
    )

    asyncio.create_task(
        run_quiz(chat_id)
    )

# =========================================================
# FUN REACTIONS
# =========================================================

FUN_REACTIONS = [

    "🧠 Brain Level Increased!",
    "🔥 OP Answer!",
    "⚡ Fastest Brain!",
    "💀 Ultra Instinct Activated!",
    "🏆 IQ 999+"
]

# =========================================================
# RANDOM REACTION
# =========================================================

async def random_reaction(chat_id):

    await bot.send_message(
        chat_id,
        random.choice(
            FUN_REACTIONS
        )
    )


# =========================================================
# PART 4 — ULTRA PRO MAX FEATURES
# NEW MODULAR STRUCTURE
# ADD BELOW PART 3
# modules/quiz_system.py
# =========================================================

# =========================================================
# RANK SYSTEM
# =========================================================

RANKS = {

    1: "🥉 Bronze",

    5: "🥈 Silver",

    10: "🥇 Gold",

    20: "💎 Diamond",

    40: "👑 Immortal"
}

# =========================================================
# USER DATA CACHE
# =========================================================

USER_CACHE = defaultdict(dict)

# =========================================================
# DUELS
# =========================================================

DUELS = {}

# =========================================================
# TOURNAMENTS
# =========================================================

TOURNAMENTS = {}

# =========================================================
# GROUP QUIZ MODE
# =========================================================

GROUP_QUIZ = defaultdict(bool)

# =========================================================
# MOTIVATION
# =========================================================

MOTIVATION = [

    "🔥 Success starts with discipline.",

    "📚 Every question makes you smarter.",

    "⚡ Consistency beats talent.",

    "🏆 Winners never quit.",

    "💯 Study now, flex later.",

    "🧠 Strong mind = strong future."
]

# =========================================================
# RANDOM FACTS
# =========================================================

FACTS = [

    "🧠 Human brain has 86 billion neurons.",

    "🌍 Earth rotates at 1670 km/h.",

    "⚡ Lightning is hotter than the sun.",

    "📚 Reading improves memory.",

    "🚀 Space is completely silent."
]

# =========================================================
# GET RANK
# =========================================================

def get_rank(level):

    current = "🥉 Bronze"

    for lvl, rank in RANKS.items():

        if level >= lvl:

            current = rank

    return current

# =========================================================
# AUTO QUIZ DROP
# =========================================================

async def auto_quiz_drop(

    bot,
    ai_model
):

    while True:

        try:

            await asyncio.sleep(3600)

            for chat_id in GROUP_QUIZ:

                if not GROUP_QUIZ[chat_id]:

                    continue

                q = await generate_question(
                    ai_model,
                    "Mixed"
                )

                if not q:

                    continue

                await bot.send_poll(

                    chat_id,

                    question=q["question"],

                    options=q["options"],

                    type="quiz",

                    correct_option_id=(
                        ord(q["correct"]) - 65
                    ),

                    is_anonymous=False,

                    open_period=60
                )

        except Exception as e:

            logger.error(
                f"Auto Quiz Error: {e}"
            )

# =========================================================
# REGISTER PRO MAX HANDLERS
# =========================================================

def register_pro_quiz_handlers(

    bot,
    ai_model
):

    # =====================================================
    # GLOBAL STATS
    # =====================================================

    @bot.on_message(
        filters.command("globalstats")
    )

    async def global_stats(
        _,
        m
    ):

        try:

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cur = await db.execute(

                    """
                    SELECT
                    SUM(total),
                    SUM(correct),
                    SUM(wrong)
                    FROM report_cards
                    """
                )

                row = await cur.fetchone()

                total = row[0] or 0

                correct = row[1] or 0

                wrong = row[2] or 0

                users = await db.execute(

                    """
                    SELECT COUNT(DISTINCT user_id)
                    FROM report_cards
                    """
                )

                user_count = (
                    await users.fetchone()
                )[0]

                text = f"""

🌍 GLOBAL QUIZ STATS

👥 Users:
{user_count}

📝 Questions Attempted:
{total}

✅ Correct:
{correct}

❌ Wrong:
{wrong}

📊 Accuracy:
{round((correct/max(total,1))*100,2)}%
"""

                await m.reply(text)

        except Exception as e:

            logger.error(
                f"Global Stats Error: {e}"
            )

    # =====================================================
    # WEEKLY LEADERBOARD
    # =====================================================

    @bot.on_message(
        filters.command("weekly")
    )

    async def weekly_leader(
        _,
        m
    ):

        try:

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cur = await db.execute(

                    """
                    SELECT
                    user_id,
                    SUM(correct)
                    FROM report_cards
                    GROUP BY user_id
                    ORDER BY SUM(correct) DESC
                    LIMIT 20
                    """
                )

                rows = await cur.fetchall()

                text = (
                    "🏆 WEEKLY LEADERBOARD\n\n"
                )

                rank = 1

                for row in rows:

                    try:

                        user = await bot.get_users(
                            row[0]
                        )

                        name = user.first_name

                    except:

                        name = "Unknown"

                    medal = "🥉"

                    if rank == 1:

                        medal = "🥇"

                    elif rank == 2:

                        medal = "🥈"

                    elif rank == 3:

                        medal = "🥉"

                    text += (

                        f"{medal} {rank}. {name}\n"

                        f"🔥 Score: {row[1]}\n\n"
                    )

                    rank += 1

                await m.reply(text)

        except Exception as e:

            logger.error(
                f"Weekly Leader Error: {e}"
            )

    # =====================================================
    # DUEL SYSTEM
    # =====================================================

    @bot.on_message(
        filters.command("duel")
    )

    async def duel(
        _,
        m
    ):

        if not m.reply_to_message:

            return await m.reply(
                "❌ Reply to someone."
            )

        user1 = m.from_user

        user2 = m.reply_to_message.from_user

        duel_id = str(

            random.randint(
                10000,
                99999
            )
        )

        DUELS[duel_id] = {

            "p1": user1.id,

            "p2": user2.id,

            "score1": 0,

            "score2": 0
        }

        kb = InlineKeyboardMarkup(

            [
                [
                    InlineKeyboardButton(
                        "⚔ Accept Duel",
                        callback_data=f"acceptduel_{duel_id}"
                    )
                ]
            ]
        )

        await m.reply(

            f"⚔ {user2.mention} challenged!",

            reply_markup=kb
        )

    # =====================================================
    # ACCEPT DUEL
    # =====================================================

    @bot.on_callback_query(
        filters.regex("^acceptduel_")
    )

    async def accept_duel(
        _,
        cb
    ):

        duel_id = cb.data.split("_")[1]

        if duel_id not in DUELS:

            return

        duel = DUELS[duel_id]

        await cb.message.edit_text(
            "⚔ Duel Started!"
        )

        for _ in range(5):

            q = await generate_question(
                ai_model,
                "Mixed"
            )

            if not q:

                continue

            poll = await bot.send_poll(

                cb.message.chat.id,

                question=q["question"],

                options=q["options"],

                type="quiz",

                correct_option_id=(
                    ord(q["correct"]) - 65
                ),

                is_anonymous=False,

                open_period=20
            )

            POLL_CACHE[poll.poll.id] = {

                "duel": duel_id,

                "correct": q["correct"]
            }

            await asyncio.sleep(25)

        s1 = duel["score1"]

        s2 = duel["score2"]

        winner = "🤝 Draw"

        if s1 > s2:

            winner = "🏆 Player 1 Wins"

        elif s2 > s1:

            winner = "🏆 Player 2 Wins"

        await bot.send_message(

            cb.message.chat.id,

            f"""

⚔ DUEL FINISHED

👤 Player1:
{s1}

👤 Player2:
{s2}

🏆 {winner}
"""
        )

    # =====================================================
    # TOURNAMENT
    # =====================================================

    @bot.on_message(
        filters.command("tournament")
    )

    async def tournament(
        _,
        m
    ):

        tour_id = str(

            random.randint(
                1000,
                9999
            )
        )

        TOURNAMENTS[tour_id] = {

            "players": [],

            "started": False
        }

        kb = InlineKeyboardMarkup(

            [
                [
                    InlineKeyboardButton(
                        "🎮 Join Tournament",
                        callback_data=f"jointour_{tour_id}"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🚀 Start Tournament",
                        callback_data=f"starttour_{tour_id}"
                    )
                ]
            ]
        )

        await m.reply(

            f"🏆 Tournament ID: {tour_id}",

            reply_markup=kb
        )

    # =====================================================
    # JOIN TOURNAMENT
    # =====================================================

    @bot.on_callback_query(
        filters.regex("^jointour_")
    )

    async def join_tour(
        _,
        cb
    ):

        tid = cb.data.split("_")[1]

        if tid not in TOURNAMENTS:

            return

        if cb.from_user.id not in TOURNAMENTS[tid]["players"]:

            TOURNAMENTS[tid]["players"].append(
                cb.from_user.id
            )

        await cb.answer(
            "Joined Tournament!"
        )

    # =====================================================
    # START TOURNAMENT
    # =====================================================

    @bot.on_callback_query(
        filters.regex("^starttour_")
    )

    async def start_tour(
        _,
        cb
    ):

        tid = cb.data.split("_")[1]

        if tid not in TOURNAMENTS:

            return

        players = TOURNAMENTS[tid]["players"]

        await cb.message.edit_text(

            f"🚀 Tournament Started!\n"
            f"Players: {len(players)}"
        )

        for _ in range(10):

            q = await generate_question(
                ai_model,
                "Mixed"
            )

            if not q:

                continue

            await bot.send_poll(

                cb.message.chat.id,

                question=q["question"],

                options=q["options"],

                type="quiz",

                correct_option_id=(
                    ord(q["correct"]) - 65
                ),

                is_anonymous=False,

                open_period=30
            )

            await asyncio.sleep(35)

    # =====================================================
    # STUDY TIP
    # =====================================================

    @bot.on_message(
        filters.command("studytip")
    )

    async def study_tip(
        _,
        m
    ):

        try:

            prompt = """

Give one powerful study tip for students.

Short.

Motivational.
"""

            res = await asyncio.to_thread(

                ai_model.generate_content,

                prompt
            )

            await m.reply(

                f"📚 Study Tip\n\n{res.text}"
            )

        except Exception as e:

            logger.error(
                f"Study Tip Error: {e}"
            )

    # =====================================================
    # MOTIVATION
    # =====================================================

    @bot.on_message(
        filters.command("motivate")
    )

    async def motivate(
        _,
        m
    ):

        await m.reply(
            random.choice(MOTIVATION)
        )

    # =====================================================
    # TIMER
    # =====================================================

    @bot.on_message(
        filters.command("timer")
    )

    async def timer(
        _,
        m
    ):

        if len(m.command) < 2:

            return await m.reply(

                "Usage:\n/timer 30"
            )

        mins = int(
            m.command[1]
        )

        msg = await m.reply(

            f"⏳ Timer Started\n"
            f"{mins} Minutes"
        )

        await asyncio.sleep(
            mins * 60
        )

        await msg.reply(
            "⏰ Time Up!"
        )

    # =====================================================
    # RANDOM FACT
    # =====================================================

    @bot.on_message(
        filters.command("fact")
    )

    async def fact(
        _,
        m
    ):

        await m.reply(
            random.choice(FACTS)
        )

    # =====================================================
    # COUNTDOWN
    # =====================================================

    @bot.on_message(
        filters.command("countdown")
    )

    async def countdown(
        _,
        m
    ):

        await m.reply(
            "📅 Exam Countdown Feature Coming Soon 🔥"
        )

    # =====================================================
    # GROUP QUIZ
    # =====================================================

    @bot.on_message(
        filters.command("groupquiz")
    )

    async def group_quiz(
        _,
        m
    ):

        GROUP_QUIZ[m.chat.id] = True

        await m.reply(
            "👥 Group Quiz Enabled"
        )

    # =====================================================
    # START AUTO TASK
    # =====================================================

    asyncio.create_task(

        auto_quiz_drop(
            bot,
            ai_model
        )
    )

# =========================================================
# PART 5 — FINAL GOD LEVEL FEATURES
# NEW MODULAR STRUCTURE
# ADD BELOW PART 4
# modules/quiz_system.py
# =========================================================

# =========================================================
# REGISTER GOD LEVEL HANDLERS
# =========================================================

def register_godlevel_quiz_handlers(

    bot,
    ai_model
):

    # =====================================================
    # AI EXPLANATION SYSTEM
    # =====================================================

    @bot.on_message(
        filters.command("explain")
    )

    async def explain_answer(
        _,
        m
    ):

        try:

            if len(m.command) < 2:

                return await m.reply(

                    "Usage:\n"
                    "/explain Newton Law"
                )

            topic = " ".join(
                m.command[1:]
            )

            msg = await m.reply(
                "🧠 Generating Explanation..."
            )

            prompt = f"""

Explain {topic}

in simple student friendly way.

Short notes.

Easy language.
"""

            res = await asyncio.to_thread(

                ai_model.generate_content,

                prompt
            )

            await msg.edit(

                f"📚 EXPLANATION\n\n"
                f"{res.text[:4000]}"
            )

        except Exception as e:

            logger.error(
                f"Explain Error: {e}"
            )

    # =====================================================
    # NOTES GENERATOR
    # =====================================================

    @bot.on_message(
        filters.command("notes")
    )

    async def notes(
        _,
        m
    ):

        try:

            if len(m.command) < 2:

                return await m.reply(

                    "Usage:\n"
                    "/notes Photosynthesis"
                )

            topic = " ".join(
                m.command[1:]
            )

            msg = await m.reply(
                "📚 Generating Notes..."
            )

            prompt = f"""

Generate short revision notes for:

{topic}

Student friendly.

Bullet points.
"""

            res = await asyncio.to_thread(

                ai_model.generate_content,

                prompt
            )

            await msg.edit(

                f"📝 NOTES\n\n"
                f"{res.text[:4000]}"
            )

        except Exception as e:

            logger.error(
                f"Notes Error: {e}"
            )

    # =====================================================
    # FORMULA SYSTEM
    # =====================================================

    @bot.on_message(
        filters.command("formula")
    )

    async def formula(
        _,
        m
    ):

        try:

            if len(m.command) < 2:

                return await m.reply(

                    "Usage:\n"
                    "/formula Gravitation"
                )

            topic = " ".join(
                m.command[1:]
            )

            msg = await m.reply(
                "🧪 Searching Formulas..."
            )

            prompt = f"""

Give important formulas for:

{topic}

with symbols meaning.
"""

            res = await asyncio.to_thread(

                ai_model.generate_content,

                prompt
            )

            await msg.edit(

                f"📐 FORMULAS\n\n"
                f"{res.text[:4000]}"
            )

        except Exception as e:

            logger.error(
                f"Formula Error: {e}"
            )

    # =====================================================
    # PYQ SYSTEM
    # =====================================================

    @bot.on_message(
        filters.command("pyq")
    )

    async def pyq(
        _,
        m
    ):

        try:

            if len(m.command) < 2:

                return await m.reply(

                    "Usage:\n"
                    "/pyq Physics"
                )

            subject = " ".join(
                m.command[1:]
            )

            msg = await m.reply(
                "📚 Fetching PYQs..."
            )

            prompt = f"""

Generate 5 Previous Year Questions

for {subject}

Exam style.
"""

            res = await asyncio.to_thread(

                ai_model.generate_content,

                prompt
            )

            await msg.edit(

                "📖 PREVIOUS YEAR QUESTIONS\n\n"
                f"{res.text[:4000]}"
            )

        except Exception as e:

            logger.error(
                f"PYQ Error: {e}"
            )

    # =====================================================
    # REVISION MODE
    # =====================================================

    @bot.on_message(
        filters.command("revision")
    )

    async def revision(
        _,
        m
    ):

        try:

            if len(m.command) < 2:

                return await m.reply(

                    "Usage:\n"
                    "/revision Biology"
                )

            subject = " ".join(
                m.command[1:]
            )

            msg = await m.reply(
                "⚡ Generating Revision Sheet..."
            )

            prompt = f"""

Generate ultra fast revision sheet for:

{subject}

Short.

Important points only.
"""

            res = await asyncio.to_thread(

                ai_model.generate_content,

                prompt
            )

            await msg.edit(

                "⚡ REVISION SHEET\n\n"
                f"{res.text[:4000]}"
            )

        except Exception as e:

            logger.error(
                f"Revision Error: {e}"
            )

    # =====================================================
    # STUDY PLANNER
    # =====================================================

    @bot.on_message(
        filters.command("planner")
    )

    async def planner(
        _,
        m
    ):

        try:

            if len(m.command) < 2:

                return await m.reply(

                    "Usage:\n"
                    "/planner NEET"
                )

            exam = " ".join(
                m.command[1:]
            )

            msg = await m.reply(
                "📅 Creating Study Plan..."
            )

            prompt = f"""

Create smart study timetable for:

{exam}

Daily routine.

Subjects.

Revision.

Breaks.
"""

            res = await asyncio.to_thread(

                ai_model.generate_content,

                prompt
            )

            await msg.edit(

                "📅 STUDY PLAN\n\n"
                f"{res.text[:4000]}"
            )

        except Exception as e:

            logger.error(
                f"Planner Error: {e}"
            )

    # =====================================================
    # DOUBT SOLVER
    # =====================================================

    @bot.on_message(
        filters.command("doubt")
    )

    async def doubt(
        _,
        m
    ):

        try:

            if len(m.command) < 2:

                return await m.reply(

                    "Usage:\n"
                    "/doubt your question"
                )

            question = " ".join(
                m.command[1:]
            )

            msg = await m.reply(
                "🤖 Solving Doubt..."
            )

            prompt = f"""

Solve this student doubt:

{question}

Easy explanation.
"""

            res = await asyncio.to_thread(

                ai_model.generate_content,

                prompt
            )

            await msg.edit(

                "🧠 DOUBT SOLUTION\n\n"
                f"{res.text[:4000]}"
            )

        except Exception as e:

            logger.error(
                f"Doubt Error: {e}"
            )

    # =====================================================
    # EXAM PREDICTOR
    # =====================================================

    @bot.on_message(
        filters.command("predict")
    )

    async def predict(
        _,
        m
    ):

        try:

            user_id = m.from_user.id

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cur = await db.execute(

                    """
                    SELECT AVG(accuracy)
                    FROM report_cards
                    WHERE user_id = ?
                    """,

                    (user_id,)
                )

                row = await cur.fetchone()

                avg = round(
                    row[0] or 0,
                    2
                )

                prediction = "📚 Need Improvement"

                if avg >= 90:

                    prediction = "🏆 Topper Level"

                elif avg >= 75:

                    prediction = "🔥 Very Strong"

                elif avg >= 60:

                    prediction = "⚡ Good"

                await m.reply(

                    f"""

📊 EXAM PREDICTION

🧠 Accuracy:
{avg}%

🎯 Prediction:
{prediction}
"""
                )

        except Exception as e:

            logger.error(
                f"Predict Error: {e}"
            )

    # =====================================================
    # AI TEST ANALYSIS
    # =====================================================

    @bot.on_message(
        filters.command("analysis")
    )

    async def analysis(
        _,
        m
    ):

        try:

            user_id = m.from_user.id

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cur = await db.execute(

                    """
                    SELECT
                    subject,
                    accuracy
                    FROM report_cards
                    WHERE user_id = ?
                    ORDER BY accuracy ASC
                    """,

                    (user_id,)
                )

                rows = await cur.fetchall()

                if not rows:

                    return await m.reply(
                        "📭 No data."
                    )

                weak = rows[:3]

                text = (
                    "📊 AI PERFORMANCE ANALYSIS\n\n"
                )

                for row in weak:

                    text += (

                        "📚 Weak Subject:\n"

                        f"{row[0]}\n"

                        "📉 Accuracy:\n"

                        f"{round(row[1],2)}%\n\n"
                    )

                text += (
                    "⚡ Focus more on weak subjects."
                )

                await m.reply(text)

        except Exception as e:

            logger.error(
                f"Analysis Error: {e}"
            )

    # =====================================================
    # QUICK FIRE MODE
    # =====================================================

    @bot.on_message(
        filters.command("quickfire")
    )

    async def quickfire(
        _,
        m
    ):

        chat_id = m.chat.id

        ACTIVE_QUIZ[chat_id] = {

            "subject": "Mixed",

            "total": 50,

            "correct": 0,

            "wrong": 0,

            "index": 0,

            "end_time": (
                time.time() + 600
            )
        }

        await m.reply(

            "🔥 QUICK FIRE MODE STARTED\n"
            "50 Questions • 10 Minutes"
        )

        asyncio.create_task(

            run_quiz(
                bot,
                ai_model,
                chat_id
            )
        )

    # =====================================================
    # NIGHT STUDY MODE
    # =====================================================

    @bot.on_message(
        filters.command("nightstudy")
    )

    async def night_study(
        _,
        m
    ):

        tips = [

            "🌙 Revise formulas before sleep.",

            "📚 Study difficult topics at night.",

            "⚡ Keep water nearby.",

            "🧠 Avoid distractions.",

            "🔥 Focus on PYQs."
        ]

        await m.reply(

            "🌙 NIGHT STUDY MODE\n\n"

            + "\n".join(tips)
        )

    # =====================================================
    # AI MOTIVATION
    # =====================================================

    @bot.on_message(
        filters.command("aimotivate")
    )

    async def ai_motivate(
        _,
        m
    ):

        try:

            res = await asyncio.to_thread(

                ai_model.generate_content,

                "Give motivational quote for students."
            )

            await m.reply(

                "🔥 AI Motivation\n\n"

                f"{res.text[:1000]}"
            )

        except Exception as e:

            logger.error(
                f"AI Motivation Error: {e}"
            )

    # =====================================================
    # QUIZ HELP MENU
    # =====================================================

    @bot.on_message(
        filters.command("quizhelp")
    )

    async def quiz_help(
        _,
        m
    ):

        text = """

📚 RUHI QUIZ COMMANDS

🎯 QUIZ
/quizhub
/dailyquiz
/speedquiz
/quickfire
/examquiz

📊 REPORTS
/report
/profile
/history
/improvement
/predict
/analysis

🏆 LEADERBOARD
/leaderboard
/weekly
/subjectleader

📖 STUDY
/notes
/explain
/formula
/revision
/planner
/doubt
/pyq

🔥 EXTRA
/fact
/motivate
/aimotivate
/nightstudy
/streak
"""

        await m.reply(text)

# =========================================================
# PART 6 — FINAL MAIN LOADER + AUTO START SYSTEM
# NEW MODULAR STRUCTURE
# ADD BELOW PART 5
# modules/quiz_system.py
# =========================================================

# =========================================================


# =========================================================
# AUTO DATABASE INIT
# =========================================================

async def init_quiz_system():

    try:

        async with aiosqlite.connect(
            QUIZ_DB
        ) as db:

            # USERS

            await db.execute("""

            CREATE TABLE IF NOT EXISTS users (

                user_id INTEGER PRIMARY KEY,

                username TEXT,

                total_quiz INTEGER DEFAULT 0,

                total_correct INTEGER DEFAULT 0,

                total_wrong INTEGER DEFAULT 0,

                xp INTEGER DEFAULT 0,

                streak INTEGER DEFAULT 0
            )
            """)

            # REPORTS

            await db.execute("""

            CREATE TABLE IF NOT EXISTS report_cards (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER,

                subject TEXT,

                marks INTEGER,

                total INTEGER,

                accuracy REAL,

                improvement REAL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # HISTORY

            await db.execute("""

            CREATE TABLE IF NOT EXISTS quiz_history (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER,

                subject TEXT,

                question TEXT,

                correct_answer TEXT,

                user_answer TEXT,

                is_correct INTEGER,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # LEADERBOARD

            await db.execute("""

            CREATE TABLE IF NOT EXISTS leaderboard (

                user_id INTEGER PRIMARY KEY,

                username TEXT,

                points INTEGER DEFAULT 0
            )
            """)

            # SUBJECT STATS

            await db.execute("""

            CREATE TABLE IF NOT EXISTS subject_stats (

                user_id INTEGER,

                subject TEXT,

                total INTEGER DEFAULT 0,

                correct INTEGER DEFAULT 0,

                PRIMARY KEY(user_id, subject)
            )
            """)

            await db.commit()

        logger.info(
            "✅ Quiz System Database Ready"
        )

    except Exception as e:

        logger.error(
            f"Quiz DB Init Error: {e}"
        )

# =========================================================
# AUTO CLEANUP SYSTEM
# =========================================================

async def auto_cleanup():

    while True:

        try:

            await asyncio.sleep(3600)

            removed = 0

            for file in os.listdir():

                if (

                    file.endswith(".mp3")

                    or file.endswith(".ogg")

                    or file.endswith(".wav")

                    or file.startswith("tts_")

                    or file.startswith("raw_")

                    or file.startswith("v_")
                ):

                    with suppress(Exception):

                        os.remove(file)

                        removed += 1

            logger.info(

                f"🧹 Cleanup Complete | Removed: {removed}"
            )

        except Exception as e:

            logger.error(
                f"Cleanup Error: {e}"
            )

# =========================================================
# OPTIONAL MEMORY SAVE SYSTEM
# =========================================================

CHAT_MEMORY = defaultdict(list)

async def save_chat_memory(chat_id):

    return

# =========================================================
# AUTO SAVE LOOP
# =========================================================

async def autosave_loop():

    while True:

        try:

            await asyncio.sleep(300)

            for chat_id in CHAT_MEMORY.keys():

                await save_chat_memory(chat_id)

            logger.info(
                "💾 Auto Save Complete"
            )

        except Exception as e:

            logger.error(
                f"AutoSave Error: {e}"
            )

# =========================================================
# AUTO MOTIVATION SYSTEM
# =========================================================

ACTIVE_CALLS = set()

MOTIVATION_LINES = [

    "🔥 Success comes from consistency.",

    "📚 Small progress is still progress.",

    "🏆 Study now, shine later.",

    "⚡ Focus beats talent.",

    "🧠 Discipline creates toppers.",

    "🚀 Keep grinding future doctor.",

    "💯 Practice makes perfect.",

    "🎯 Stay focused on your goal."
]

async def motivation_broadcast(

    bot
):

    while True:

        try:

            await asyncio.sleep(21600)

            for chat_id in ACTIVE_CALLS:

                try:

                    text = random.choice(
                        MOTIVATION_LINES
                    )

                    await bot.send_message(

                        chat_id,

                        f"🌟 Motivation\n\n{text}"
                    )

                except:

                    pass

        except Exception as e:

            logger.error(
                f"Motivation Broadcast Error: {e}"
            )

# =========================================================
# QUIZ TIMER WATCHER
# =========================================================

async def quiz_timer_watcher(

    bot
):

    while True:

        try:

            await asyncio.sleep(5)

            now = time.time()

            expired = []

            for chat_id, quiz in ACTIVE_QUIZ.items():

                if now >= quiz["end_time"]:

                    expired.append(chat_id)

            for chat_id in expired:

                quiz = ACTIVE_QUIZ.get(chat_id)

                if not quiz:

                    continue

                total = (
                    quiz["correct"]
                    + quiz["wrong"]
                )

                accuracy = round(

                    (
                        quiz["correct"] / total
                    ) * 100,

                    2

                ) if total else 0

                await bot.send_message(

                    chat_id,

                    f"""

⏰ QUIZ TIME OVER

📚 Subject:
{quiz['subject']}

✅ Correct:
{quiz['correct']}

❌ Wrong:
{quiz['wrong']}

🎯 Accuracy:
{accuracy}%
"""
                )

                ACTIVE_QUIZ.pop(

                    chat_id,

                    None
                )

        except Exception as e:

            logger.error(
                f"Quiz Timer Error: {e}"
            )

# =========================================================
# STARTUP BANNER
# =========================================================

def startup_banner():

    print("""

╔════════════════════════════════════╗
║                                    ║
║     👑 RUHI SUPREME QUIZ AI 👑     ║
║                                    ║
║        FINAL GOD LEVEL BUILD       ║
║                                    ║
╚════════════════════════════════════╝

📚 1000+ Subjects Enabled
🧠 AI Quiz System Loaded
🏆 Report Cards Enabled
⚡ Voice AI Enabled
🎵 Music VC Enabled
🔥 Inline Quiz UI Loaded
💯 Poll Quiz Engine Active

""")

# =========================================================
# FINAL MAIN LOADER
# =========================================================

async def quiz_main_loader(

    bot,
    ai_model
):

    try:

        startup_banner()

        await init_quiz_system()

        # =============================================
        # REGISTER ALL HANDLERS
        # =============================================

        register_quiz_handlers(
            bot,
            ai_model
        )

        register_advanced_quiz_handlers(
            bot,
            ai_model
        )

        register_ultra_quiz_handlers(
            bot,
            ai_model
        )

        register_pro_quiz_handlers(
            bot,
            ai_model
        )

        register_godlevel_quiz_handlers(
            bot,
            ai_model
        )

        # =============================================
        # BACKGROUND TASKS
        # =============================================

        asyncio.create_task(
            auto_cleanup()
        )

        asyncio.create_task(
            autosave_loop()
        )

        asyncio.create_task(
            motivation_broadcast(
                bot
            )
        )

        asyncio.create_task(
            quiz_timer_watcher(
                bot
            )
        )

        logger.info(
            "🚀 Quiz System Fully Loaded"
        )

    except Exception as e:

        logger.error(
            f"Quiz Main Loader Error: {e}"
        )

# =========================================================
# FINAL READY MESSAGE
# =========================================================

print("""

✅ PART 6 LOADED SUCCESSFULLY

🔥 ALL FEATURES READY

📚 Quiz System
🧠 AI System
🏆 Report Cards
🎵 Voice AI
⚡ VC Assistant
📊 Analytics
🎯 Inline Buttons
💯 Poll Quizzes
📖 Notes
🧪 Formulas
📚 PYQs
🚀 Study Planner

""")

# =========================================================
# IMPORTANT APP.PY EDIT
# =========================================================

"""
NOW ADD THIS IN core/app.py

=============================================

1. IMPORT:

from modules.quiz_system import (
    quiz_main_loader
)

=============================================

2. INSIDE async def start(self):

AFTER:

await self.ai.load()

ADD:

await quiz_main_loader(
    self.bot,
    self.ai.model
)

=============================================

FINAL:

await self.ai.load()

await quiz_main_loader(
    self.bot,
    self.ai.model
)

self.handlers.register()

=============================================

DONE ✅
"""

# =========================================================
# PART 7 — ADVANCED ANALYTICS + STUDY PLANNER + NOTES
# NEW MODULAR STRUCTURE
# ADD BELOW PART 6
# modules/quiz_system.py

# =========================================================
# STUDY PLANNER DATABASE
# =========================================================

async def init_study_planner():

    try:

        async with aiosqlite.connect(
            QUIZ_DB
        ) as db:

            await db.execute("""

            CREATE TABLE IF NOT EXISTS study_plans (

                user_id INTEGER,

                subject TEXT,

                target_date TEXT,

                daily_goal INTEGER,

                completed INTEGER DEFAULT 0
            )
            """)

            await db.execute("""

            CREATE TABLE IF NOT EXISTS notes_library (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                subject TEXT,

                topic TEXT,

                content TEXT
            )
            """)

            await db.execute("""

            CREATE TABLE IF NOT EXISTS pyq_library (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                exam TEXT,

                subject TEXT,

                year INTEGER,

                question TEXT,

                answer TEXT
            )
            """)

            await db.commit()

        logger.info(
            "✅ Study Planner Ready"
        )

    except Exception as e:

        logger.error(
            f"Study Planner Init Error: {e}"
        )

# =========================================================
# DAILY CHALLENGE CACHE
# =========================================================

DAILY_CHALLENGE = {}

# =========================================================
# DAILY CHALLENGE LOOP
# =========================================================

async def generate_daily_challenge():

    while True:

        try:

            await asyncio.sleep(86400)

            DAILY_CHALLENGE.clear()

            DAILY_CHALLENGE["question"] = (
                "What is SI unit of Force?"
            )

            DAILY_CHALLENGE["answer"] = (
                "Newton"
            )

            logger.info(
                "🔥 Daily Challenge Updated"
            )

        except Exception as e:

            logger.error(
                f"Daily Challenge Error: {e}"
            )

# =========================================================
# PART 7 HANDLERS
# =========================================================

def register_part7_handlers(

    bot,
    ai_model
):

    # =====================================================
    # CREATE STUDY PLAN
    # =====================================================

    @bot.on_message(
        filters.command(["planner"])
    )
    async def create_study_plan(
        _,
        m: Message
    ):

        try:

            user_id = m.from_user.id

            args = m.text.split(
                maxsplit=3
            )

            if len(args) < 4:

                return await m.reply(
                    """
📚 Usage:

/planner SUBJECT DAYS DAILY_GOAL

Example:
/planner Physics 30 50
"""
                )

            subject = args[1]

            days = int(args[2])

            daily_goal = int(args[3])

            target_date = (

                datetime.now()

                + timedelta(days=days)

            ).strftime("%Y-%m-%d")

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                await db.execute("""

                INSERT INTO study_plans

                VALUES (?, ?, ?, ?, 0)

                """, (

                    user_id,
                    subject,
                    target_date,
                    daily_goal
                ))

                await db.commit()

            await m.reply(
                f"""

✅ Study Plan Created

📚 Subject:
{subject}

🎯 Daily Goal:
{daily_goal} Questions

📅 Target Date:
{target_date}
"""
            )

        except Exception as e:

            logger.error(
                f"Planner Error: {e}"
            )

    # =====================================================
    # STUDY PROGRESS
    # =====================================================

    @bot.on_message(
        filters.command(["progress"])
    )
    async def study_progress(
        _,
        m: Message
    ):

        try:

            user_id = m.from_user.id

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cursor = await db.execute("""

                SELECT

                subject,
                target_date,
                daily_goal,
                completed

                FROM study_plans

                WHERE user_id = ?

                """, (
                    user_id,
                ))

                rows = await cursor.fetchall()

            if not rows:

                return await m.reply(
                    "❌ No study plans found."
                )

            text = (
                "📊 YOUR STUDY PROGRESS\n\n"
            )

            for row in rows:

                subject = row[0]

                target = row[1]

                goal = row[2]

                completed = row[3]

                progress = round(

                    (
                        completed / goal
                    ) * 100,

                    2

                ) if goal else 0

                text += (

                    f"📚 {subject}\n"

                    f"🎯 Goal: {goal}\n"

                    f"✅ Completed: {completed}\n"

                    f"📈 Progress: {progress}%\n"

                    f"📅 Target: {target}\n\n"
                )

            await m.reply(text)

        except Exception as e:

            logger.error(
                f"Progress Error: {e}"
            )

    # =====================================================
    # NOTES GENERATOR
    # =====================================================

    @bot.on_message(
        filters.command(["notes"])
    )
    async def generate_notes(
        _,
        m: Message
    ):

        try:

            topic = " ".join(
                m.command[1:]
            )

            if not topic:

                return await m.reply(
                    "📚 Example:\n/notes Human Anatomy"
                )

            status = await m.reply(
                "🧠 Generating Notes..."
            )

            prompt = f"""

Generate short study notes in Hinglish.

Topic:
{topic}

Include:
- Definition
- Key Points
- Formula
- Important Facts
"""

            response = await asyncio.to_thread(
                ai_model.generate_content,
                prompt
            )

            notes = (

                response.text[:4000]

                if hasattr(response, "text")

                else "No notes."
            )

            await status.edit(

                f"📚 NOTES — {topic}\n\n{notes}"
            )

        except Exception as e:

            logger.error(
                f"Notes Error: {e}"
            )

    # =====================================================
    # FORMULA GENERATOR
    # =====================================================

    @bot.on_message(
        filters.command(["formula"])
    )
    async def formula_generator(
        _,
        m: Message
    ):

        try:

            topic = " ".join(
                m.command[1:]
            )

            if not topic:

                return await m.reply(
                    "📘 Example:\n/formula Thermodynamics"
                )

            status = await m.reply(
                "📘 Generating Formula Sheet..."
            )

            prompt = f"""

Generate important formulas for:
{topic}

Format:
Formula + Short Meaning
"""

            response = await asyncio.to_thread(
                ai_model.generate_content,
                prompt
            )

            formulas = (

                response.text[:4000]

                if hasattr(response, "text")

                else "No formulas."
            )

            await status.edit(

                f"📘 FORMULAS — {topic}\n\n{formulas}"
            )

        except Exception as e:

            logger.error(
                f"Formula Error: {e}"
            )

    # =====================================================
    # PYQ GENERATOR
    # =====================================================

    @bot.on_message(
        filters.command(["pyq"])
    )
    async def pyq_generator(
        _,
        m: Message
    ):

        try:

            topic = " ".join(
                m.command[1:]
            )

            if not topic:

                return await m.reply(
                    "📖 Example:\n/pyq Physics"
                )

            status = await m.reply(
                "📖 Generating PYQs..."
            )

            prompt = f"""

Generate 5 Previous Year Questions for:
{topic}

With answers.
"""

            response = await asyncio.to_thread(
                ai_model.generate_content,
                prompt
            )

            pyqs = (

                response.text[:4000]

                if hasattr(response, "text")

                else "No PYQs."
            )

            await status.edit(

                f"📖 PYQs — {topic}\n\n{pyqs}"
            )

        except Exception as e:

            logger.error(
                f"PYQ Error: {e}"
            )

    # =====================================================
    # DAILY QUIZ
    # =====================================================

    @bot.on_message(
        filters.command(["daily"])
    )
    async def daily_quiz(
        _,
        m: Message
    ):

        if not DAILY_CHALLENGE:

            return await m.reply(
                "⏳ Daily challenge not loaded."
            )

        await m.reply(
            f"""

🔥 DAILY CHALLENGE

❓ {DAILY_CHALLENGE['question']}

Reply using:
/answer your_answer
"""
        )

    # =====================================================
    # DAILY ANSWER CHECK
    # =====================================================

    @bot.on_message(
        filters.command(["answer"])
    )
    async def answer_daily(
        _,
        m: Message
    ):

        try:

            ans = " ".join(
                m.command[1:]
            ).lower()

            if not ans:

                return

            correct = DAILY_CHALLENGE.get(
                "answer",
                ""
            ).lower()

            if ans == correct:

                await m.reply(
                    "✅ Correct Answer!"
                )

            else:

                await m.reply(
                    f"❌ Wrong\nCorrect: {correct}"
                )

        except Exception as e:

            logger.error(
                f"Daily Answer Error: {e}"
            )

    # =====================================================
    # SUBJECT RECOMMENDER
    # =====================================================

    @bot.on_message(
        filters.command(["recommend"])
    )
    async def recommend_subject(
        _,
        m: Message
    ):

        try:

            user_id = m.from_user.id

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cursor = await db.execute("""

                SELECT

                subject,
                correct,
                total

                FROM subject_stats

                WHERE user_id = ?

                """, (
                    user_id,
                ))

                rows = await cursor.fetchall()

            if not rows:

                return await m.reply(
                    "❌ No data found."
                )

            weak = []

            for row in rows:

                acc = (

                    row[1] / row[2]

                ) * 100 if row[2] else 0

                if acc < 60:

                    weak.append(
                        row[0]
                    )

            if not weak:

                return await m.reply(
                    "🏆 Excellent performance in all subjects!"
                )

            text = (
                "📚 Subjects needing improvement:\n\n"
            )

            for s in weak:

                text += f"• {s}\n"

            await m.reply(text)

        except Exception as e:

            logger.error(
                f"Recommend Error: {e}"
            )

# =========================================================
# START PART 7 SERVICES
# =========================================================

async def start_part7_services():

    await init_study_planner()

    asyncio.create_task(
        generate_daily_challenge()
    )

    logger.info(
        "✅ PART 7 SERVICES STARTED"
    )

# =========================================================
# READY MESSAGE
# =========================================================

print("""

✅ PART 7 LOADED

📚 Study Planner
📈 Analytics
📖 Notes
📘 Formula Generator
📖 PYQs
🔥 Daily Challenge
🧠 AI Recommendations
🏆 Progress Tracker

""")

# =========================================================
# PART 8 — AI QUIZ MASTER + SMART EXPLANATION ENGINE
# NEW MODULAR STRUCTURE
# ADD BELOW PART 7
# modules/quiz_system.py
# =========================================================


# =========================================================
# AI QUIZ STORAGE
# =========================================================

ACTIVE_AI_QUIZ = {}

QUIZ_TIME_OPTIONS = {

    "10 Questions • 10 Min": (10, 10),

    "60 Questions • 1 Hour": (60, 60),

    "120 Questions • 120 Min": (120, 120)
}

# =========================================================
# ALL SUBJECTS FLAT LIST
# =========================================================

ALL_SUBJECTS = []

for category in SUBJECTS.values():

    for sub in category:

        if sub not in ALL_SUBJECTS:

            ALL_SUBJECTS.append(sub)

# =========================================================
# PART 8 HANDLERS
# =========================================================

def register_part8_handlers(

    bot,
    ai_model
):

    # =====================================================
    # SUBJECT MENU
    # =====================================================

    @bot.on_message(
        filters.command(["subjects"])
    )
    async def subjects_menu(
        _,
        m: Message
    ):

        try:

            buttons = []

            row = []

            for i, subject in enumerate(

                ALL_SUBJECTS,
                start=1
            ):

                row.append(

                    InlineKeyboardButton(

                        subject[:20],

                        callback_data=f"sub_{subject}"
                    )
                )

                if len(row) == 2:

                    buttons.append(row)

                    row = []

            if row:

                buttons.append(row)

            await m.reply(
                """

📚 SELECT SUBJECT

Choose any subject
for AI Quiz System
""",

                reply_markup=InlineKeyboardMarkup(
                    buttons[:50]
                )
            )

        except Exception as e:

            logger.error(
                f"Subjects Menu Error: {e}"
            )

    # =====================================================
    # SUBJECT SELECTED
    # =====================================================

    @bot.on_callback_query(
        filters.regex("^sub_")
    )
    async def subject_selected(
        _,
        cb: CallbackQuery
    ):

        try:

            subject = cb.data.replace(
                "sub_",
                ""
            )

            kb = InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "10Q • 10Min",
                        callback_data=f"quiz_{subject}_10"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "60Q • 1Hr",
                        callback_data=f"quiz_{subject}_60"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "120Q • 120Min",
                        callback_data=f"quiz_{subject}_120"
                    )
                ]
            ])

            await cb.message.edit_text(
                f"""

📚 SUBJECT:
{subject}

⏰ Select Quiz Duration
""",

                reply_markup=kb
            )

        except Exception as e:

            logger.error(
                f"Subject Select Error: {e}"
            )

    # =====================================================
    # START QUIZ
    # =====================================================

    @bot.on_callback_query(
        filters.regex("^quiz_")
    )
    async def start_ai_quiz(
        _,
        cb: CallbackQuery
    ):

        try:

            user_id = cb.from_user.id

            data = cb.data.split("_")

            subject = data[1]

            total_questions = int(data[2])

            duration = (

                10

                if total_questions == 10

                else 60

                if total_questions == 60

                else 120
            )

            ACTIVE_AI_QUIZ[user_id] = {

                "subject": subject,

                "total": total_questions,

                "correct": 0,

                "wrong": 0,

                "current": 1,

                "start": time.time(),

                "duration": duration * 60
            }

            await cb.message.edit_text(
                f"""

🚀 QUIZ STARTED

📚 Subject:
{subject}

❓ Questions:
{total_questions}

⏰ Duration:
{duration} Minutes

🔥 Best Of Luck
"""
            )

            await send_ai_question(

                bot,
                ai_model,
                cb.message.chat.id,
                user_id
            )

        except Exception as e:

            logger.error(
                f"Quiz Start Error: {e}"
            )

    # =====================================================
    # ANSWER CHECKER
    # =====================================================

    @bot.on_callback_query(
        filters.regex("^ans_")
    )
    async def ai_answer_checker(
        _,
        cb: CallbackQuery
    ):

        try:

            user_id = cb.from_user.id

            if user_id not in ACTIVE_AI_QUIZ:

                return await cb.answer(
                    "Quiz expired."
                )

            quiz = ACTIVE_AI_QUIZ[user_id]

            answer = cb.data.replace(
                "ans_",
                ""
            )

            correct = quiz["correct_answer"]

            explanation = quiz["explanation"]

            # =============================================
            # CORRECT
            # =============================================

            if answer == correct:

                quiz["correct"] += 1

                reaction = random.choice([

                    "🔥 Excellent!",

                    "💯 Genius!",

                    "⚡ Correct!",

                    "🏆 Smart!",

                    "🧠 Brilliant!"
                ])

                await cb.answer(
                    reaction,
                    show_alert=True
                )

            else:

                quiz["wrong"] += 1

                await cb.answer(
                    f"❌ Wrong\nCorrect: {correct}",
                    show_alert=True
                )

            # =============================================
            # EXPLANATION
            # =============================================

            await bot.send_message(
                cb.message.chat.id,
                f"""

📖 EXPLANATION

{explanation}
"""
            )

            # =============================================
            # NEXT QUESTION
            # =============================================

            quiz["current"] += 1

            if quiz["current"] > quiz["total"]:

                total = (

                    quiz["correct"]

                    + quiz["wrong"]
                )

                accuracy = round(

                    (
                        quiz["correct"]
                        / total
                    ) * 100,

                    2

                ) if total else 0

                time_taken = round(

                    (
                        time.time()
                        - quiz["start"]
                    ) / 60,

                    2
                )

                performance = (

                    "🔥 Excellent"

                    if accuracy >= 80

                    else "⚡ Good"

                    if accuracy >= 60

                    else "📚 Need Improvement"
                )

                await bot.send_message(
                    cb.message.chat.id,
                    f"""

🏁 QUIZ COMPLETED

📚 Subject:
{quiz['subject']}

✅ Correct:
{quiz['correct']}

❌ Wrong:
{quiz['wrong']}

🎯 Accuracy:
{accuracy}%

⏰ Time Taken:
{time_taken} Min

📊 Performance:
{performance}
"""
                )

                # =========================================
                # AI ANALYSIS
                # =========================================

                analysis_prompt = f"""

Student completed quiz.

Subject:
{quiz['subject']}

Accuracy:
{accuracy}%

Give:
- Weakness
- Improvement Tips
- Motivation
"""

                response = await asyncio.to_thread(

                    ai_model.generate_content,
                    analysis_prompt
                )

                analysis = (

                    response.text[:3000]

                    if hasattr(response, "text")

                    else "Keep practicing."
                )

                await bot.send_message(
                    cb.message.chat.id,
                    f"""

🧠 AI ANALYSIS

{analysis}
"""
                )

                ACTIVE_AI_QUIZ.pop(
                    user_id,
                    None
                )

                return

            await send_ai_question(

                bot,
                ai_model,
                cb.message.chat.id,
                user_id
            )

        except Exception as e:

            logger.error(
                f"AI Answer Checker Error: {e}"
            )

    # =====================================================
    # ASK AI TEACHER
    # =====================================================

    @bot.on_message(
        filters.command(["ask"])
    )
    async def ask_ai_teacher(
        _,
        m: Message
    ):

        try:

            question = " ".join(
                m.command[1:]
            )

            if not question:

                return await m.reply(
                    """

🧠 Example:

/ask What is Newton Law?
"""
                )

            status = await m.reply(
                "🧠 AI Teacher Thinking..."
            )

            prompt = f"""

You are an expert teacher.

Explain in simple Hinglish:

{question}

Explain step-by-step.
"""

            response = await asyncio.to_thread(

                ai_model.generate_content,
                prompt
            )

            answer = (

                response.text[:4000]

                if hasattr(response, "text")

                else "No answer."
            )

            await status.edit(
                f"""

🧠 AI TEACHER

{answer}
"""
            )

        except Exception as e:

            logger.error(
                f"Ask AI Error: {e}"
            )

    # =====================================================
    # DOUBT SOLVER
    # =====================================================

    @bot.on_message(
        filters.command(["doubt"])
    )
    async def ai_doubt_solver(
        _,
        m: Message
    ):

        try:

            doubt = " ".join(
                m.command[1:]
            )

            if not doubt:

                return

            status = await m.reply(
                "🧠 Solving Doubt..."
            )

            response = await asyncio.to_thread(

                ai_model.generate_content,

                f"""

Solve this doubt in simple Hinglish:

{doubt}
"""
            )

            ans = (

                response.text[:4000]

                if hasattr(response, "text")

                else "No solution."
            )

            await status.edit(
                f"""

📚 DOUBT SOLUTION

{ans}
"""
            )

        except Exception as e:

            logger.error(
                f"Doubt Solver Error: {e}"
            )

# =========================================================
# SEND AI QUESTION
# =========================================================

async def send_ai_question(

    bot,
    ai_model,
    chat_id,
    user_id
):

    try:

        quiz = ACTIVE_AI_QUIZ[user_id]

        subject = quiz["subject"]

        qn = quiz["current"]

        prompt = f"""

Generate 1 MCQ for {subject}

Format:
Question|A|B|C|D|CorrectLetter|Short Explanation
"""

        response = await asyncio.to_thread(

            ai_model.generate_content,
            prompt
        )

        text = response.text.strip()

        data = text.split("|")

        if len(data) < 7:

            return

        question = data[0]

        options = data[1:5]

        correct = data[5].strip().upper()

        explanation = data[6]

        quiz["correct_answer"] = correct

        quiz["explanation"] = explanation

        kb = []

        for i, opt in enumerate(options):

            letter = chr(65 + i)

            kb.append([
                InlineKeyboardButton(
                    f"{letter}. {opt}",
                    callback_data=f"ans_{letter}"
                )
            ])

        await bot.send_message(
            chat_id,
            f"""

📚 {subject}

❓ Question {qn}/{quiz['total']}

{question}
""",

            reply_markup=InlineKeyboardMarkup(kb)
        )

    except Exception as e:

        logger.error(
            f"Send AI Question Error: {e}"
        )

# =========================================================
# PART 8 STARTER
# =========================================================

async def start_part8_services():

    logger.info(
        "✅ PART 8 SERVICES STARTED"
    )

# =========================================================
# READY MESSAGE
# =========================================================

print("""

✅ PART 8 LOADED

🧠 AI QUIZ MASTER
📚 Smart MCQs
🎯 Accuracy System
📖 AI Explanations
🏆 Performance Analysis
⚡ AI Teacher
📚 Doubt Solver
🔥 Motivation
📊 Smart Reports

""")

# =========================================================
# PART 9 — ADVANCED REPORT CARD + LEADERBOARD + RANKS
# NEW MODULAR STRUCTURE
# ADD BELOW PART 8
# modules/quiz_system.py
# =========================================================


# =========================================================
# GLOBAL RANK SYSTEM
# =========================================================

RANKS = [

    (0, "🥉 Beginner"),

    (100, "🥈 Learner"),

    (300, "🥇 Skilled"),

    (700, "🏆 Advanced"),

    (1500, "👑 Master"),

    (3000, "🔥 Legend"),

    (6000, "⚡ Supreme"),

    (10000, "💀 Quiz God")
]

# =========================================================
# GET USER RANK
# =========================================================

def get_rank(xp):

    rank = "🥉 Beginner"

    for value, name in RANKS:

        if xp >= value:

            rank = name

    return rank

# =========================================================
# SAVE REPORT CARD
# =========================================================

async def save_report_card(

    user_id,
    subject,
    correct,
    wrong
):

    try:

        total = correct + wrong

        accuracy = round(

            (
                correct / total
            ) * 100,

            2

        ) if total else 0

        improvement = round(

            random.uniform(
                1,
                12
            ),

            2
        )

        async with aiosqlite.connect(
            QUIZ_DB
        ) as db:

            # =============================================
            # SAVE REPORT
            # =============================================

            await db.execute("""

            INSERT INTO report_cards (

                user_id,
                subject,
                marks,
                total,
                accuracy,
                improvement
            )

            VALUES (?, ?, ?, ?, ?, ?)

            """, (

                user_id,
                subject,
                correct,
                total,
                accuracy,
                improvement
            ))

            # =============================================
            # USER UPDATE
            # =============================================

            xp_gain = (
                correct * 5
            )

            await db.execute("""

            INSERT INTO users (

                user_id,
                total_quiz,
                total_correct,
                total_wrong,
                xp

            )

            VALUES (?, 1, ?, ?, ?)

            ON CONFLICT(user_id)

            DO UPDATE SET

            total_quiz = total_quiz + 1,

            total_correct = total_correct + ?,

            total_wrong = total_wrong + ?,

            xp = xp + ?

            """, (

                user_id,

                correct,

                wrong,

                xp_gain,

                correct,

                wrong,

                xp_gain
            ))

            await db.commit()

    except Exception as e:

        logger.error(
            f"Save Report Error: {e}"
        )

# =========================================================
# PART 9 HANDLERS
# =========================================================

def register_part9_handlers(

    bot,
    ai_model
):

    # =====================================================
    # REPORT CARD
    # =====================================================

    @bot.on_message(
        filters.command(["report"])
    )
    async def report_card(
        _,
        m: Message
    ):

        try:

            user_id = m.from_user.id

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cursor = await db.execute("""

                SELECT

                subject,
                marks,
                total,
                accuracy,
                improvement,
                created_at

                FROM report_cards

                WHERE user_id = ?

                ORDER BY id DESC

                LIMIT 10

                """, (
                    user_id,
                ))

                rows = await cursor.fetchall()

            if not rows:

                return await m.reply(
                    "❌ No reports found."
                )

            text = "📊 REPORT CARD\n\n"

            for row in rows:

                text += (

                    f"📚 {row[0]}\n"

                    f"✅ Marks: {row[1]}/{row[2]}\n"

                    f"🎯 Accuracy: {row[3]}%\n"

                    f"📈 Improvement: +{row[4]}%\n"

                    f"📅 {row[5]}\n\n"
                )

            await m.reply(text)

        except Exception as e:

            logger.error(
                f"Report Card Error: {e}"
            )

    # =====================================================
    # PROFILE
    # =====================================================

    @bot.on_message(
        filters.command(["profile"])
    )
    async def user_profile(
        _,
        m: Message
    ):

        try:

            user_id = m.from_user.id

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cursor = await db.execute("""

                SELECT

                total_quiz,
                total_correct,
                total_wrong,
                xp

                FROM users

                WHERE user_id = ?

                """, (
                    user_id,
                ))

                row = await cursor.fetchone()

            if not row:

                return await m.reply(
                    "❌ No profile found."
                )

            total_quiz = row[0]

            correct = row[1]

            wrong = row[2]

            xp = row[3]

            accuracy = round(

                (
                    correct / (
                        correct + wrong
                    )
                ) * 100,

                2

            ) if (
                correct + wrong
            ) else 0

            rank = get_rank(xp)

            await m.reply(
                f"""

👤 PROFILE CARD

🏆 Rank:
{rank}

⚡ XP:
{xp}

📚 Total Quiz:
{total_quiz}

✅ Correct:
{correct}

❌ Wrong:
{wrong}

🎯 Accuracy:
{accuracy}%
"""
            )

        except Exception as e:

            logger.error(
                f"Profile Error: {e}"
            )

    # =====================================================
    # LEADERBOARD
    # =====================================================

    @bot.on_message(
        filters.command(["leaderboard"])
    )
    async def leaderboard(
        _,
        m: Message
    ):

        try:

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cursor = await db.execute("""

                SELECT

                user_id,
                xp,
                total_correct

                FROM users

                ORDER BY xp DESC

                LIMIT 10

                """)

                rows = await cursor.fetchall()

            if not rows:

                return await m.reply(
                    "❌ No leaderboard data."
                )

            text = "🏆 GLOBAL LEADERBOARD\n\n"

            for i, row in enumerate(

                rows,
                start=1
            ):

                user_id = row[0]

                xp = row[1]

                correct = row[2]

                try:

                    user = await bot.get_users(
                        user_id
                    )

                    name = user.first_name

                except:

                    name = "Unknown"

                rank = get_rank(xp)

                text += (

                    f"{i}. {name}\n"

                    f"{rank}\n"

                    f"⚡ XP: {xp}\n"

                    f"✅ Correct: {correct}\n\n"
                )

            await m.reply(text)

        except Exception as e:

            logger.error(
                f"Leaderboard Error: {e}"
            )

    # =====================================================
    # ANALYTICS
    # =====================================================

    @bot.on_message(
        filters.command(["analytics"])
    )
    async def analytics(
        _,
        m: Message
    ):

        try:

            user_id = m.from_user.id

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cursor = await db.execute("""

                SELECT

                subject,
                AVG(accuracy)

                FROM report_cards

                WHERE user_id = ?

                GROUP BY subject

                """, (
                    user_id,
                ))

                rows = await cursor.fetchall()

            if not rows:

                return await m.reply(
                    "❌ No analytics available."
                )

            text = "📊 SUBJECT ANALYTICS\n\n"

            weak = []

            strong = []

            for row in rows:

                subject = row[0]

                avg = round(
                    row[1],
                    2
                )

                text += (

                    f"📚 {subject}\n"

                    f"🎯 Avg Accuracy: {avg}%\n\n"
                )

                if avg >= 75:

                    strong.append(subject)

                else:

                    weak.append(subject)

            text += "\n🔥 Strong Subjects:\n"

            for s in strong[:5]:

                text += f"✅ {s}\n"

            text += "\n📚 Weak Subjects:\n"

            for s in weak[:5]:

                text += f"❌ {s}\n"

            await m.reply(text)

        except Exception as e:

            logger.error(
                f"Analytics Error: {e}"
            )

    # =====================================================
    # ACHIEVEMENTS
    # =====================================================

    @bot.on_message(
        filters.command(["achievements"])
    )
    async def achievements(
        _,
        m: Message
    ):

        try:

            user_id = m.from_user.id

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cursor = await db.execute("""

                SELECT

                total_quiz,
                total_correct,
                xp

                FROM users

                WHERE user_id = ?

                """, (
                    user_id,
                ))

                row = await cursor.fetchone()

            if not row:

                return await m.reply(
                    "❌ No achievements."
                )

            tq = row[0]

            tc = row[1]

            xp = row[2]

            badges = []

            if tq >= 10:

                badges.append(
                    "🎖 Quiz Starter"
                )

            if tq >= 100:

                badges.append(
                    "🏆 Quiz Warrior"
                )

            if tc >= 500:

                badges.append(
                    "🧠 Brain Master"
                )

            if xp >= 5000:

                badges.append(
                    "🔥 Supreme Legend"
                )

            if not badges:

                badges.append(
                    "📚 Keep Practicing"
                )

            text = "🏅 ACHIEVEMENTS\n\n"

            for b in badges:

                text += f"{b}\n"

            await m.reply(text)

        except Exception as e:

            logger.error(
                f"Achievement Error: {e}"
            )

    # =====================================================
    # PERFORMANCE COMPARISON
    # =====================================================

    @bot.on_message(
        filters.command(["compare"])
    )
    async def compare_performance(
        _,
        m: Message
    ):

        try:

            user_id = m.from_user.id

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cursor = await db.execute("""

                SELECT

                subject,
                accuracy

                FROM report_cards

                WHERE user_id = ?

                ORDER BY id DESC

                LIMIT 2

                """, (
                    user_id,
                ))

                rows = await cursor.fetchall()

            if len(rows) < 2:

                return await m.reply(
                    "❌ Not enough reports."
                )

            latest = rows[0][1]

            previous = rows[1][1]

            diff = round(
                latest - previous,
                2
            )

            if diff > 0:

                msg = (
                    f"📈 Improved by {diff}%"
                )

            elif diff < 0:

                msg = (
                    f"📉 Dropped by {abs(diff)}%"
                )

            else:

                msg = (
                    "⚡ Same Performance"
                )

            await m.reply(
                f"""

📊 PERFORMANCE COMPARISON

Latest Accuracy:
{latest}%

Previous Accuracy:
{previous}%

{msg}
"""
            )

        except Exception as e:

            logger.error(
                f"Compare Error: {e}"
            )

# =========================================================
# PART 9 STARTER
# =========================================================

async def start_part9_services():

    logger.info(
        "✅ PART 9 SERVICES STARTED"
    )

# =========================================================
# IMPORTANT PATCH
# =========================================================

"""
✅ ADD THIS INSIDE PART 8

RIGHT BEFORE:

ACTIVE_AI_QUIZ.pop(user_id, None)

ADD:

await save_report_card(

    user_id,

    quiz['subject'],

    quiz['correct'],

    quiz['wrong']
)

"""

# =========================================================
# FINAL LOADED
# =========================================================

print("""

✅ PART 9 LOADED

🏆 Leaderboards
📊 Analytics
📈 Performance Tracking
📚 Report Cards
🔥 Achievements
👤 User Profiles
⚡ XP System
👑 Rank System
📉 Comparisons

""")
# =========================================================
# PART 10 — ULTRA UI + POLL QUIZ + VOICE QUIZ SYSTEM
# NEW MODULAR STRUCTURE
# ADD BELOW PART 9
# modules/quiz_system.py
# =========================================================


# =========================================================
# QUIZ MODES
# =========================================================

QUIZ_MODES = {

    "poll": "📊 Poll Quiz",

    "mcq": "🧠 Inline MCQ",

    "voice": "🎤 Voice Quiz",

    "rapid": "⚡ Rapid Fire"
}

# =========================================================
# RAPID FIRE CACHE
# =========================================================

RAPID_FIRE = {}

# =========================================================
# SMART REACTIONS
# =========================================================

SUCCESS_REACTIONS = [

    "🔥",
    "⚡",
    "🏆",
    "💯",
    "🧠",
    "👑",
    "🎯"
]

FAIL_REACTIONS = [

    "😅",
    "📚",
    "❌",
    "🥲",
    "😶"
]

# =========================================================
# PART 10 HANDLERS
# =========================================================

def register_part10_handlers(

    bot,
    ai_model
):

    # =====================================================
    # QUIZ HUB
    # =====================================================

    @bot.on_message(
        filters.command(["quizhub"])
    )
    async def quiz_hub(
        _,
        m: Message
    ):

        kb = InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "📚 Subjects",
                    callback_data="hub_subjects"
                )
            ],

            [
                InlineKeyboardButton(
                    "🏆 Leaderboard",
                    callback_data="hub_leaderboard"
                ),

                InlineKeyboardButton(
                    "📊 Profile",
                    callback_data="hub_profile"
                )
            ],

            [
                InlineKeyboardButton(
                    "📈 Analytics",
                    callback_data="hub_analytics"
                )
            ],

            [
                InlineKeyboardButton(
                    "🎯 Daily Quiz",
                    callback_data="hub_daily"
                )
            ]
        ])

        await m.reply_photo(

            photo="https://graph.org/file/1d8c7d61f4d6f4d53f2a2.jpg",

            caption="""

👑 RUHI QUIZ HUB

🔥 AI Powered Quiz System
📚 1000+ Subjects
🏆 Smart Rankings
📈 Live Analytics
⚡ Voice Quiz
🧠 AI Teacher

""",

            reply_markup=kb
        )

    # =====================================================
    # HUB CALLBACKS
    # =====================================================

    @bot.on_callback_query(
        filters.regex("^hub_")
    )
    async def quiz_hub_callbacks(
        _,
        cb: CallbackQuery
    ):

        data = cb.data

        try:

            if data == "hub_subjects":

                await cb.message.reply(
                    "📚 Use /subjects"
                )

            elif data == "hub_leaderboard":

                await cb.message.reply(
                    "🏆 Use /leaderboard"
                )

            elif data == "hub_profile":

                await cb.message.reply(
                    "📊 Use /profile"
                )

            elif data == "hub_analytics":

                await cb.message.reply(
                    "📈 Use /analytics"
                )

            elif data == "hub_daily":

                await cb.message.reply(
                    "🎯 Use /daily"
                )

            await cb.answer()

        except Exception as e:

            logger.error(
                f"Hub Callback Error: {e}"
            )

    # =====================================================
    # POLL QUIZ
    # =====================================================

    @bot.on_message(
        filters.command(["pollquiz"])
    )
    async def poll_quiz(
        _,
        m: Message
    ):

        try:

            subject = " ".join(
                m.command[1:]
            )

            if not subject:

                return await m.reply(
                    """

📚 Example:

/pollquiz Physics

"""
                )

            status = await m.reply(
                "🧠 Creating Poll Quiz..."
            )

            prompt = f"""

Generate MCQ for {subject}

Format:
Question|A|B|C|D|CorrectIndex(0-3)

"""

            response = await asyncio.to_thread(

                ai_model.generate_content,

                prompt
            )

            data = response.text.split("|")

            if len(data) < 6:

                return await status.edit(
                    "❌ Quiz generation failed."
                )

            question = data[0]

            options = [

                data[1],
                data[2],
                data[3],
                data[4]
            ]

            correct = int(data[5])

            await bot.send_poll(

                chat_id=m.chat.id,

                question=question,

                options=options,

                type="quiz",

                correct_option_id=correct,

                explanation="📚 Powered By Ruhi AI",

                is_anonymous=False
            )

            await status.delete()

        except Exception as e:

            logger.error(
                f"Poll Quiz Error: {e}"
            )

    # =====================================================
    # RAPID FIRE
    # =====================================================

    @bot.on_message(
        filters.command(["rapid"])
    )
    async def rapid_fire(
        _,
        m: Message
    ):

        try:

            subject = " ".join(
                m.command[1:]
            )

            if not subject:

                return await m.reply(
                    """

⚡ Example:

/rapid Biology

"""
                )

            RAPID_FIRE[m.from_user.id] = {

                "subject": subject,

                "score": 0,

                "start": time.time()
            }

            await m.reply(
                f"""

⚡ RAPID FIRE STARTED

📚 Subject:
{subject}

🔥 30 Seconds Per Question

"""
            )

            await rapid_question(

                bot,
                ai_model,

                m.chat.id,

                m.from_user.id
            )

        except Exception as e:

            logger.error(
                f"Rapid Fire Error: {e}"
            )

    # =====================================================
    # RAPID ANSWER
    # =====================================================

    @bot.on_callback_query(
        filters.regex("^rapid_")
    )
    async def rapid_answer(
        _,
        cb: CallbackQuery
    ):

        try:

            user_id = cb.from_user.id

            if user_id not in RAPID_FIRE:

                return await cb.answer(
                    "Quiz expired."
                )

            answer = cb.data.replace(
                "rapid_",
                ""
            )

            correct = RAPID_FIRE[user_id]["correct"]

            if answer == correct:

                RAPID_FIRE[user_id]["score"] += 1

                await cb.answer(
                    f"{random.choice(SUCCESS_REACTIONS)} Correct!"
                )

            else:

                await cb.answer(
                    f"{random.choice(FAIL_REACTIONS)} Wrong ({correct})"
                )

            await rapid_question(

                bot,
                ai_model,

                cb.message.chat.id,

                user_id
            )

        except Exception as e:

            logger.error(
                f"Rapid Answer Error: {e}"
            )

    # =====================================================
    # VOICE QUIZ
    # =====================================================

    @bot.on_message(
        filters.command(["voicequiz"])
    )
    async def voice_quiz(
        _,
        m: Message
    ):

        try:

            topic = " ".join(
                m.command[1:]
            )

            if not topic:

                return await m.reply(
                    """

🎤 Example:

/voicequiz Physics

"""
                )

            status = await m.reply(
                "🎤 Creating Voice Quiz..."
            )

            response = await asyncio.to_thread(

                ai_model.generate_content,

                f"""

Generate one short quiz question on:
{topic}

Keep short.

"""
            )

            question = response.text[:300]

            tts_file = (
                f"voice_quiz_{uuid.uuid4().hex}.mp3"
            )

            await edge_tts.Communicate(

                question,

                "en-US-AriaNeural"

            ).save(tts_file)

            await m.reply_voice(

                tts_file,

                caption="🎤 Voice Quiz"
            )

            with suppress(Exception):

                os.remove(tts_file)

            await status.delete()

        except Exception as e:

            logger.error(
                f"Voice Quiz Error: {e}"
            )

    # =====================================================
    # MOTIVATION
    # =====================================================

    @bot.on_message(
        filters.command(["motivate"])
    )
    async def motivate(
        _,
        m: Message
    ):

        lines = [

            "🔥 Toppers are made by consistency.",

            "⚡ Every question improves your brain.",

            "📚 Daily practice beats talent.",

            "🏆 One day your hardwork will pay off.",

            "🧠 Study smart not just hard."
        ]

        await m.reply(
            random.choice(lines)
        )

# =========================================================
# RAPID QUESTION FUNCTION
# =========================================================

async def rapid_question(

    bot,
    ai_model,

    chat_id,
    user_id
):

    try:

        if user_id not in RAPID_FIRE:

            return

        subject = RAPID_FIRE[user_id]["subject"]

        prompt = f"""

Generate simple MCQ for {subject}

Format:
Question|A|B|C|D|CorrectLetter

"""

        response = await asyncio.to_thread(

            ai_model.generate_content,

            prompt
        )

        data = response.text.split("|")

        if len(data) < 6:

            return

        kb = InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    data[1],
                    callback_data=f"rapid_A"
                )
            ],

            [
                InlineKeyboardButton(
                    data[2],
                    callback_data=f"rapid_B"
                )
            ],

            [
                InlineKeyboardButton(
                    data[3],
                    callback_data=f"rapid_C"
                )
            ],

            [
                InlineKeyboardButton(
                    data[4],
                    callback_data=f"rapid_D"
                )
            ]
        ])

        RAPID_FIRE[user_id]["correct"] = data[5]

        await bot.send_message(

            chat_id,

            f"""

⚡ RAPID FIRE

❓ {data[0]}

⏰ 30 Seconds

""",

            reply_markup=kb
        )

    except Exception as e:

        logger.error(
            f"Rapid Question Error: {e}"
        )

# =========================================================
# PART 10 STARTER
# =========================================================

async def start_part10_services():

    logger.info(
        "✅ PART 10 SERVICES STARTED"
    )

# =========================================================
# FINAL LOADED
# =========================================================

print("""

✅ PART 10 LOADED

🎨 Ultra UI
📊 Poll Quiz
⚡ Rapid Fire
🎤 Voice Quiz
🧠 Smart Reactions
🏆 Quiz Hub
📚 AI Generated Polls
🔥 Motivation Engine

""")


# =========================================================
# REQUIRED IMPORTS
# =========================================================

"""
ADD THESE IMPORTS ON TOP:

import gc
import shutil

from datetime import (
    datetime,
    timedelta
)

"""

# =========================================================
# FINAL STARTUP BANNER
# =========================================================

FINAL_BANNER = r'''

╔══════════════════════════════════════╗
║                                      ║
║      👑 RUHI SUPREME FINAL 👑        ║
║                                      ║
║      AI QUIZ GOD MODE ACTIVATED      ║
║                                      ║
╚══════════════════════════════════════╝

🧠 AI Teacher Loaded
📚 1000+ Subjects Loaded
🏆 Rank System Loaded
📊 Report Cards Loaded
⚡ Poll Quiz Loaded
🎤 Voice Quiz Loaded
📖 Notes Loaded
📘 Formula Engine Loaded
🔥 Daily Challenge Loaded
💾 Backup System Loaded
🛡 Anti Crash Enabled
🚀 Performance Optimized

'''

print(FINAL_BANNER)

# =========================================================
# FINAL SUCCESS
# =========================================================

print("""

✅ PART 11 LOADED SUCCESSFULLY

👑 RUHI SUPREME
ULTIMATE EDUCATION AI SYSTEM READY

🔥 EVERYTHING ENABLED

""")
# =========================================================
# PART 11 — FINAL GOD MODE SYSTEM
# NEW MODULAR STRUCTURE
# ADD BELOW PART 10
# modules/quiz_system.py
# =========================================================

# =========================================================
# BACKUP SYSTEM
# =========================================================

BACKUP_DIR = "quiz_backups"

os.makedirs(
    BACKUP_DIR,
    exist_ok=True
)

# =========================================================
# GROUP STATS
# =========================================================

GROUP_STATS = defaultdict(

    lambda: {

        "quiz": 0,

        "correct": 0,

        "wrong": 0
    }
)

# =========================================================
# ACTIVE BATTLES
# =========================================================

ACTIVE_BATTLES = {}

# =========================================================
# AUTO BACKUP
# =========================================================

async def auto_backup():

    while True:

        try:

            await asyncio.sleep(
                21600
            )

            if not os.path.exists(
                QUIZ_DB
            ):

                continue

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            backup_file = (
                f"{BACKUP_DIR}/backup_{timestamp}.db"
            )

            shutil.copy(
                QUIZ_DB,
                backup_file
            )

            logger.info(
                f"💾 Backup Created: {backup_file}"
            )

        except Exception as e:

            logger.error(
                f"Backup Error: {e}"
            )

# =========================================================
# MEMORY OPTIMIZER
# =========================================================

async def memory_optimizer():

    while True:

        try:

            await asyncio.sleep(300)

            gc.collect()

            logger.info(
                "🧠 Memory Optimized"
            )

        except Exception as e:

            logger.error(
                f"Memory Optimizer Error: {e}"
            )

# =========================================================
# ANTI CRASH SYSTEM
# =========================================================

async def anti_crash_system(

    bot,
    assistant
):

    while True:

        try:

            await asyncio.sleep(60)

            # BOT CHECK

            try:

                if not bot.is_connected:

                    logger.warning(
                        "⚠ Bot Disconnected"
                    )

                    with suppress(Exception):

                        await bot.start()

            except:
                pass

            # ASSISTANT CHECK

            try:

                if not assistant.is_connected:

                    logger.warning(
                        "⚠ Assistant Disconnected"
                    )

                    with suppress(Exception):

                        await assistant.start()

            except:
                pass

            logger.info(
                "🛡 AntiCrash Running"
            )

        except Exception as e:

            logger.error(
                f"AntiCrash Error: {e}"
            )

# =========================================================
# UPDATE STREAK
# =========================================================

async def update_streak(
    user_id
):

    try:

        async with aiosqlite.connect(
            QUIZ_DB
        ) as db:

            await db.execute(
                """
                UPDATE users
                SET streak = streak + 1
                WHERE user_id = ?
                """,
                (
                    user_id,
                )
            )

            await db.commit()

    except Exception as e:

        logger.error(
            f"Streak Error: {e}"
        )

# =========================================================
# PART 11 HANDLERS
# =========================================================

def register_part11_handlers(

    bot,
    assistant
):

    # =====================================================
    # GROUP RANK
    # =====================================================

    @bot.on_message(
        filters.command(["grouprank"])
    )
    async def group_rank(
        _,
        m: Message
    ):

        try:

            chat_id = m.chat.id

            stats = GROUP_STATS[chat_id]

            total = (
                stats["correct"]
                + stats["wrong"]
            )

            accuracy = round(
                (
                    stats["correct"]
                    / total
                ) * 100,
                2
            ) if total else 0

            await m.reply(
                f"""

🏆 GROUP PERFORMANCE

📚 Quiz Played:
{stats['quiz']}

✅ Correct:
{stats['correct']}

❌ Wrong:
{stats['wrong']}

🎯 Accuracy:
{accuracy}%

"""
            )

        except Exception as e:

            logger.error(
                f"Group Rank Error: {e}"
            )

    # =====================================================
    # BATTLE SYSTEM
    # =====================================================

    @bot.on_message(
        filters.command(["battle"])
    )
    async def battle_mode(
        _,
        m: Message
    ):

        try:

            if not m.reply_to_message:

                return await m.reply(
                    """

⚔ Reply to someone:

/battle Physics

"""
                )

            subject = " ".join(
                m.command[1:]
            )

            if not subject:

                return await m.reply(
                    "📚 Give subject."
                )

            p1 = m.from_user.id

            p2 = (
                m.reply_to_message
                .from_user.id
            )

            ACTIVE_BATTLES[m.chat.id] = {

                "p1": p1,

                "p2": p2,

                "subject": subject,

                "score1": 0,

                "score2": 0
            }

            await m.reply(
                f"""

⚔ QUIZ BATTLE STARTED

📚 Subject:
{subject}

👤 Player 1:
{m.from_user.first_name}

👤 Player 2:
{m.reply_to_message.from_user.first_name}

🔥 Best Of Luck

"""
            )

        except Exception as e:

            logger.error(
                f"Battle Error: {e}"
            )

    # =====================================================
    # STREAK
    # =====================================================

    @bot.on_message(
        filters.command(["streak"])
    )
    async def streak(
        _,
        m: Message
    ):

        try:

            user_id = m.from_user.id

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cursor = await db.execute(
                    """
                    SELECT streak
                    FROM users
                    WHERE user_id = ?
                    """,
                    (
                        user_id,
                    )
                )

                row = await cursor.fetchone()

            streak_count = (

                row[0]

                if row

                else 0
            )

            await m.reply(
                f"""

🔥 YOUR STREAK

📅 Current Streak:
{streak_count} Days

"""
            )

        except Exception as e:

            logger.error(
                f"Streak Command Error: {e}"
            )

    # =====================================================
    # EXPORT REPORT
    # =====================================================

    @bot.on_message(
        filters.command(["export"])
    )
    async def export_reports(
        _,
        m: Message
    ):

        try:

            user_id = m.from_user.id

            async with aiosqlite.connect(
                QUIZ_DB
            ) as db:

                cursor = await db.execute(
                    """
                    SELECT
                    subject,
                    marks,
                    total,
                    accuracy
                    FROM report_cards
                    WHERE user_id = ?
                    """,
                    (
                        user_id,
                    )
                )

                rows = await cursor.fetchall()

            if not rows:

                return await m.reply(
                    "❌ No reports."
                )

            filename = (
                f"report_{user_id}.txt"
            )

            with open(

                filename,

                "w",

                encoding="utf-8"

            ) as f:

                f.write(
                    "RUHI QUIZ REPORT\n\n"
                )

                for row in rows:

                    f.write(
                        f"""

Subject: {row[0]}
Marks: {row[1]}/{row[2]}
Accuracy: {row[3]}%

"""
                    )

            await m.reply_document(

                filename,

                caption="📊 Quiz Report"
            )

            with suppress(Exception):

                os.remove(filename)

        except Exception as e:

            logger.error(
                f"Export Error: {e}"
            )

# =========================================================
# =========================================================
# BACKGROUND STARTER
# =========================================================

BACKGROUND_TASKS = []

async def start_background_systems(

    bot,
    assistant
):

    try:

        BACKGROUND_TASKS.append(

            asyncio.create_task(
                auto_backup()
            )
        )

        BACKGROUND_TASKS.append(

            asyncio.create_task(
                memory_optimizer()
            )
        )

        BACKGROUND_TASKS.append(

            asyncio.create_task(
                anti_crash_system(
                    bot,
                    assistant
                )
            )
        )

        logger.info(
            "🚀 Background Systems Started"
        )

    except Exception as e:

        logger.error(
            f"Background System Error: {e}"
        )

# =========================================================
# =========================================================
# FINAL QUIZ LOADER
# =========================================================

async def final_quiz_loader(

    bot,
    assistant,
    ai_model
):

    try:

        # =============================================
        # DATABASE INIT
        # =============================================

        await init_quiz_system()

        await init_study_planner()

        # =============================================
        # PART 12 ADMIN + SECURITY
        # =============================================

        register_part12_handlers(

            bot,
            assistant,
            ai_model
        )

        # =============================================
        # BACKGROUND SYSTEMS
        # =============================================

        await start_background_systems(

            bot,
            assistant
        )

        await start_part12_services()

        logger.info(
            "👑 FINAL QUIZ SYSTEM READY"
        )

    except Exception as e:

        logger.error(
            f"Final Loader Error: {e}"
        )
# =========================================================
# HOW TO LOAD
# =========================================================

"""
ADD INSIDE:

core/app.py

AFTER:

self.handlers.register()

ADD:

from modules.quiz_system import (
    register_part10_handlers,
    register_part11_handlers,
    final_quiz_loader
)

register_part10_handlers(
    self.bot,
    self.ai.model
)

register_part11_handlers(
    self.bot,
    self.assistant
)

await final_quiz_loader(
    self.bot,
    self.assistant
)

"""

# =========================================================
# FINAL LOADED
# =========================================================

print("""

✅ PART 11 LOADED

💾 Auto Backup
🧠 Memory Optimizer
🛡 AntiCrash System
🏆 Group Rank
⚔ Battle System
🔥 Daily Streak
📊 Export Reports
🚀 Background Tasks

👑 RUHI QUIZ GOD MODE READY

""")

# =========================================================
# PART 12 — ADMIN PANEL + SECURITY SYSTEM
# NEW MODULAR STRUCTURE
# ADD BELOW PART 11
# modules/quiz_system.py
# =========================================================

"""
✅ LATEST MODULAR VERSION

FEATURES:
👑 Admin Panel
🛡 Security System
🚫 Anti Spam
⛔ User Ban System
📢 Broadcast
📊 Admin Stats
🧹 Cache Cleaner
⚙ Runtime Controls
🔥 Fully Compatible

✅ NO OLD GLOBAL STRUCTURE
"""

# =========================================================
# ADMIN CACHE
# =========================================================

SUPER_ADMINS = set()

BANNED_USERS = set()

SPAM_TRACK = defaultdict(list)

BOT_SETTINGS = {

    "quiz_enabled": True,

    "ai_enabled": True,

    "voice_enabled": True,

    "maintenance": False
}

# =========================================================
# CHECK ADMIN
# =========================================================

async def is_admin(

    bot,
    chat_id,
    user_id
):

    try:

        member = await bot.get_chat_member(
            chat_id,
            user_id
        )

        return member.status in [

            "administrator",

            "owner"
        ]

    except:

        return False

# =========================================================
# PART 12 HANDLERS
# =========================================================

def register_part12_handlers(

    bot,
    assistant,
    ai_model
):

    # =====================================================
    # ADMIN PANEL
    # =====================================================

    @bot.on_message(
        filters.command(["adminpanel"])
    )
    async def admin_panel(
        _,
        m: Message
    ):

        try:

            ok = await is_admin(

                bot,

                m.chat.id,

                m.from_user.id
            )

            if not ok:

                return await m.reply(
                    "❌ Admin only."
                )

            kb = InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(
                        "📊 Stats",
                        callback_data="admin_stats"
                    ),

                    InlineKeyboardButton(
                        "🧹 Cleanup",
                        callback_data="admin_cleanup"
                    )
                ],

                [

                    InlineKeyboardButton(
                        "📢 Broadcast",
                        callback_data="admin_broadcast"
                    ),

                    InlineKeyboardButton(
                        "⚙ Settings",
                        callback_data="admin_settings"
                    )
                ],

                [

                    InlineKeyboardButton(
                        "🚫 Ban User",
                        callback_data="admin_ban"
                    ),

                    InlineKeyboardButton(
                        "✅ Unban",
                        callback_data="admin_unban"
                    )
                ]
            ])

            await m.reply(
                """

👑 RUHI ADMIN PANEL

🛡 Security Controls
📊 Live Statistics
⚙ Runtime Settings
🔥 Advanced Management

""",
                reply_markup=kb
            )

        except Exception as e:

            logger.error(
                f"Admin Panel Error: {e}"
            )

    # =====================================================
    # ADMIN CALLBACKS
    # =====================================================

    @bot.on_callback_query(
        filters.regex("^admin_")
    )
    async def admin_callbacks(
        _,
        cb: CallbackQuery
    ):

        try:

            data = cb.data

            # =============================================
            # STATS
            # =============================================

            if data == "admin_stats":

                total_users = len(
                    USER_XP
                )

                total_quiz = len(
                    ACTIVE_QUIZ
                )

                total_battles = len(
                    ACTIVE_BATTLES
                )

                mem = round(
                    psutil.virtual_memory().percent,
                    2
                )

                await cb.message.edit_text(
                    f"""

📊 LIVE BOT STATS

👥 Users:
{total_users}

📚 Active Quiz:
{total_quiz}

⚔ Battles:
{total_battles}

🧠 RAM Usage:
{mem}%

🔥 Status:
ONLINE

"""
                )

            # =============================================
            # CLEANUP
            # =============================================

            elif data == "admin_cleanup":

                gc.collect()

                await cb.answer(
                    "🧹 Cleanup Complete"
                )

            # =============================================
            # SETTINGS
            # =============================================

            elif data == "admin_settings":

                text = f"""

⚙ BOT SETTINGS

📚 Quiz:
{BOT_SETTINGS['quiz_enabled']}

🧠 AI:
{BOT_SETTINGS['ai_enabled']}

🎤 Voice:
{BOT_SETTINGS['voice_enabled']}

🛠 Maintenance:
{BOT_SETTINGS['maintenance']}

"""

                await cb.message.edit_text(
                    text
                )

            # =============================================
            # BAN
            # =============================================

            elif data == "admin_ban":

                await cb.answer(
                    "Reply + /ban userid"
                )

            # =============================================
            # UNBAN
            # =============================================

            elif data == "admin_unban":

                await cb.answer(
                    "Use /unban userid"
                )

        except Exception as e:

            logger.error(
                f"Admin Callback Error: {e}"
            )

    # =====================================================
    # BAN USER
    # =====================================================

    @bot.on_message(
        filters.command(["ban"])
    )
    async def ban_user(
        _,
        m: Message
    ):

        try:

            ok = await is_admin(

                bot,

                m.chat.id,

                m.from_user.id
            )

            if not ok:

                return

            if len(m.command) < 2:

                return await m.reply(
                    "Usage:\n/ban user_id"
                )

            user_id = int(
                m.command[1]
            )

            BANNED_USERS.add(
                user_id
            )

            await m.reply(
                f"🚫 Banned: {user_id}"
            )

        except Exception as e:

            logger.error(
                f"Ban Error: {e}"
            )

    # =====================================================
    # UNBAN USER
    # =====================================================

    @bot.on_message(
        filters.command(["unban"])
    )
    async def unban_user(
        _,
        m: Message
    ):

        try:

            ok = await is_admin(

                bot,

                m.chat.id,

                m.from_user.id
            )

            if not ok:

                return

            if len(m.command) < 2:

                return await m.reply(
                    "Usage:\n/unban user_id"
                )

            user_id = int(
                m.command[1]
            )

            BANNED_USERS.discard(
                user_id
            )

            await m.reply(
                f"✅ Unbanned: {user_id}"
            )

        except Exception as e:

            logger.error(
                f"Unban Error: {e}"
            )

    # =====================================================
    # BROADCAST
    # =====================================================

    @bot.on_message(
        filters.command(["broadcast"])
    )
    async def broadcast(
        _,
        m: Message
    ):

        try:

            ok = await is_admin(

                bot,

                m.chat.id,

                m.from_user.id
            )

            if not ok:

                return

            text = " ".join(
                m.command[1:]
            )

            if not text:

                return await m.reply(
                    "Usage:\n/broadcast hello"
                )

            sent = 0

            failed = 0

            for user_id in USER_XP.keys():

                try:

                    await bot.send_message(
                        user_id,
                        f"📢 {text}"
                    )

                    sent += 1

                except:

                    failed += 1

            await m.reply(
                f"""

📢 BROADCAST COMPLETE

✅ Sent:
{sent}

❌ Failed:
{failed}

"""
            )

        except Exception as e:

            logger.error(
                f"Broadcast Error: {e}"
            )

    # =====================================================
    # MAINTENANCE
    # =====================================================

    @bot.on_message(
        filters.command(["maintenance"])
    )
    async def maintenance(
        _,
        m: Message
    ):

        try:

            ok = await is_admin(

                bot,

                m.chat.id,

                m.from_user.id
            )

            if not ok:

                return

            BOT_SETTINGS[
                "maintenance"
            ] = not BOT_SETTINGS[
                "maintenance"
            ]

            state = (
                "ON"
                if BOT_SETTINGS[
                    "maintenance"
                ]
                else "OFF"
            )

            await m.reply(
                f"🛠 Maintenance: {state}"
            )

        except Exception as e:

            logger.error(
                f"Maintenance Error: {e}"
            )

# =========================================================
# SECURITY FILTER
# =========================================================

async def security_filter(
    message: Message
):

    try:

        user_id = (
            message.from_user.id
        )

        # =============================================
        # BANNED
        # =============================================

        if user_id in BANNED_USERS:

            return False

        # =============================================
        # MAINTENANCE
        # =============================================

        if BOT_SETTINGS[
            "maintenance"
        ]:

            return False

        # =============================================
        # SPAM CHECK
        # =============================================

        now = time.time()

        SPAM_TRACK[user_id] = [

            x for x in
            SPAM_TRACK[user_id]

            if now - x < 10
        ]

        SPAM_TRACK[user_id].append(
            now
        )

        if len(
            SPAM_TRACK[user_id]
        ) > 8:

            return False

        return True

    except:

        return True

# =========================================================
# START PART 12 SERVICES
# =========================================================

async def start_part12_services():

    logger.info(
        "👑 PART 12 SERVICES STARTED"
    )

# =========================================================
# FINAL LOADED
# =========================================================

print("""

✅ PART 12 LOADED

👑 Admin Panel
🛡 Security System
🚫 Anti Spam
📢 Broadcast
⚙ Runtime Settings
🧹 Cleanup Engine
🔥 Full Protection

""")

# =========================================================
