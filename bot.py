import os
import re
import uuid
import random
import asyncio
import logging
import aiosqlite
import time
import json
import numpy as np

from collections import defaultdict, deque
from asyncio import Lock, Semaphore
from contextlib import suppress

import edge_tts
import google.generativeai as genai

from faster_whisper import WhisperModel
from yt_dlp import YoutubeDL

from pyrogram import Client, filters, idle
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait

from pytgcalls import PyTgCalls
from pytgcalls.exceptions import NoActiveGroupCall

from pytgcalls.types.stream.legacy.audio_piped import AudioPiped
from pytgcalls.types.stream.stream_audio_ended import StreamAudioEnded
from pytgcalls.types.raw.audio_stream import AudioStream as AudioFrame
# =========================================
# =========================================
# 1. ULTIMATE CONFIG & GLOBALS
# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("RuhiSupreme")

API_ID = 33745438
API_HASH = "142eb5aab37976e2d39475b07e8e3212"

BOT_TOKEN = ""
SESSION_STRING = ""
GEMINI_API_KEY = ""

LOGGER_ID = -1003009782265

VAD_THRESHOLD = 700
MAX_BUFFER_FRAMES = 250
MAX_PLAYLIST_SIZE = 15
MAX_QUEUE_LIMIT = 50

WAKE_WORDS = [
    "ruhi",
    "roohi"
]

VOICE = "hi-IN-SwaraNeural"

# =========================================
# AI MODELS
# =========================================

print(
    "🚀 Loading Ruhi Supreme 5.6: Bulletproof Final Build..."
)

whisper_model = WhisperModel(
    "tiny",
    device="cpu",
    compute_type="int8"
)

genai.configure(
    api_key=GEMINI_API_KEY
)

ai_model = genai.GenerativeModel(
    "gemini-1.5-flash"
)

# =========================================
# CLIENTS
# =========================================

bot = Client(
    "RuhiBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

assistant = Client(
    "RuhiAssistant",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

call_py = PyTgCalls(assistant)

# =========================================
# STATES (STABLE)
# =========================================

QUEUE = defaultdict(list)

ACTIVE_CALLS = set()

AUDIO_BUFFER = defaultdict(list)

CHAT_LOCKS = defaultdict(Lock)

TTS_LOCK = defaultdict(Lock)

VOICE_LOCK = defaultdict(Lock)

CPU_SHIELD = Semaphore(2)

ACTIVE_CALLS_LOCK = Lock()

IS_PROCESSING = defaultdict(bool)

TTS_PLAYING = defaultdict(bool)

SILENCE_COUNT = defaultdict(int)

VOLUME = defaultdict(
    lambda: 100
)

PLAY_START_TIME = defaultdict(float)

GAME_STATE = defaultdict(
    lambda: [""] * 9
)

QUIZ_DATA = defaultdict(str)

CHAT_MEMORY = defaultdict(
    lambda: deque(maxlen=5)
)

AI_COOLDOWN = defaultdict(
    lambda: 0
)

CB_COOLDOWN = defaultdict(
    lambda: 0
)

PLAY_COOLDOWN = defaultdict(
    lambda: 0
)
#=========================================

# =========================================
# =========================================
# 2. DATABASE & PERSISTENCE (FINAL FIXED)
# =========================================

async def init_db():

    async with aiosqlite.connect(
        "ruhi_supreme.db"
    ) as db:

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                score INTEGER DEFAULT 0
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                chat_id INTEGER PRIMARY KEY,
                context TEXT
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS p_queue (
                chat_id INTEGER,
                title TEXT,
                url TEXT
            )
            """
        )

        await db.commit()


async def update_score(user_id):

    try:

        async with aiosqlite.connect(
            "ruhi_supreme.db"
        ) as db:

            await db.execute(
                """
                INSERT INTO stats (
                    user_id,
                    score
                )
                VALUES (?, 1)
                ON CONFLICT(user_id)
                DO UPDATE SET
                score = score + 1
                """,
                (user_id,)
            )

            await db.commit()

    except Exception as e:

        logger.error(
            f"Update Score Error: {e}"
        )


async def save_chat_memory(chat_id):

    try:

        context = json.dumps(
            list(CHAT_MEMORY[chat_id])
        )

        async with aiosqlite.connect(
            "ruhi_supreme.db"
        ) as db:

            await db.execute(
                """
                INSERT OR REPLACE INTO memory
                VALUES (?, ?)
                """,
                (
                    chat_id,
                    context
                )
            )

            await db.commit()

    except Exception as e:

        logger.error(
            f"Save Memory Error: {e}"
        )


async def load_memories():

    try:

        async with aiosqlite.connect(
            "ruhi_supreme.db"
        ) as db:

            async with db.execute(
                "SELECT * FROM memory"
            ) as cursor:

                async for row in cursor:

                    if row[1]:

                        try:

                            CHAT_MEMORY[row[0]] = deque(
                                json.loads(row[1]),
                                maxlen=5
                            )

                        except Exception as e:

                            logger.error(
                                f"Memory Load Error: {e}"
                            )

    except Exception as e:

        logger.error(
            f"Load Memories Error: {e}"
        )


async def remove_song_db(chat_id, title):

    try:

        async with aiosqlite.connect(
            "ruhi_supreme.db"
        ) as db:

            await db.execute(
                """
                DELETE FROM p_queue
                WHERE chat_id = ?
                AND title = ?
                """,
                (
                    chat_id,
                    title
                )
            )

            await db.commit()

    except Exception as e:

        logger.error(
            f"Remove Song DB Error: {e}"
        )


async def clear_queue_db(chat_id):

    try:

        async with aiosqlite.connect(
            "ruhi_supreme.db"
        ) as db:

            await db.execute(
                """
                DELETE FROM p_queue
                WHERE chat_id = ?
                """,
                (chat_id,)
            )

            await db.commit()

    except Exception as e:

        logger.error(
            f"Clear Queue DB Error: {e}"
        )


# =========================================
# 3. QUEUE RECOVERY (FINAL FIXED)
# =========================================

async def recover_queue():

    await asyncio.sleep(5)

    try:

        async with aiosqlite.connect(
            "ruhi_supreme.db"
        ) as db:

            async with db.execute(
                """
                SELECT *
                FROM p_queue
                """
            ) as cursor:

                async for row in cursor:

                    chat_id, title, url = row

                    if not any(
                        x["url"] == url
                        for x in QUEUE[chat_id]
                    ):

                        QUEUE[chat_id].append(
                            {
                                "title": title,
                                "url": url
                            }
                        )

        for chat_id in list(QUEUE.keys()):

            if (
                chat_id not in ACTIVE_CALLS
                and QUEUE[chat_id]
            ):

                try:

                    await call_py.join_group_call(
                        chat_id,
                        AudioPiped(
                            "https://raw.githubusercontent.com/TheHamkerCat/WilliamButcherBot/master/cache/empty.aac"
                        )
                    )

                    ACTIVE_CALLS.add(chat_id)

                    await asyncio.sleep(2)

                    asyncio.create_task(
                        play_next(chat_id)
                    )

                except Exception as e:

                    logger.error(
                        f"Recovery Fail in {chat_id}: {e}"
                    )

        logger.info(
            "✅ Queue Recovery Complete"
        )

    except Exception as e:

        logger.error(
            f"Recover Queue Error: {e}"
        )
#=========================================

#=========================================
#=========================================
#4. GAMES LOGIC (FINAL FIXED)
#=========================================

def smart_ttt_move(board):

    try:

        ws = [
            (0,1,2),
            (3,4,5),
            (6,7,8),
            (0,3,6),
            (1,4,7),
            (2,5,8),
            (0,4,8),
            (2,4,6)
        ]

        # Win / Block Logic
        for char in ["⭕", "❌"]:

            for a, b, c in ws:

                line = [
                    board[a],
                    board[b],
                    board[c]
                ]

                if (
                    line.count(char) == 2
                    and line.count("") == 1
                ):

                    return [a, b, c][
                        line.index("")
                    ]

        # Center Priority
        if board[4] == "":
            return 4

        # Random Empty
        empty = [
            i for i, v in enumerate(board)
            if not v
        ]

        return (
            random.choice(empty)
            if empty
            else None
        )

    except Exception as e:

        logger.error(
            f"TTT Move Error: {e}"
        )

        return None


def get_ttt_kb(chat_id):

    try:

        b = GAME_STATE.get(
            chat_id,
            [""] * 9
        )

        kb = [
            [
                InlineKeyboardButton(
                    b[i * 3 + j] or " ",
                    callback_data=f"ttt_{i * 3 + j}"
                )
                for j in range(3)
            ]
            for i in range(3)
        ]

        kb.append(
            [
                InlineKeyboardButton(
                    "Reset 🔄",
                    callback_data="ttt_reset"
                )
            ]
        )

        return InlineKeyboardMarkup(kb)

    except Exception as e:

        logger.error(
            f"TTT Keyboard Error: {e}"
        )

        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Reset 🔄",
                        callback_data="ttt_reset"
                    )
                ]
            ]
        )


def check_ttt_winner(board):

    try:

        ws = [
            (0,1,2),
            (3,4,5),
            (6,7,8),
            (0,3,6),
            (1,4,7),
            (2,5,8),
            (0,4,8),
            (2,4,6)
        ]

        for a, b, c in ws:

            if (
                board[a]
                == board[b]
                == board[c]
                != ""
            ):

                return board[a]

        return (
            "Draw"
            if "" not in board
            else None
        )

    except Exception as e:

        logger.error(
            f"TTT Winner Error: {e}"
        )

        return None
#=========================================

#=========================================
#=========================================
#5. MUSIC ENGINE (FINAL FIXED)
#=========================================

async def handle_play(chat_id, query, msg=None, seek=0, recovery=False):

    if not query:
        return

    if len(QUEUE[chat_id]) >= MAX_QUEUE_LIMIT:

        if msg:
            await msg.edit("❌ Queue Full!")

        return

    is_playlist = (
        "list=" in query.lower()
        or "playlist" in query.lower()
    )

    search = (
        f"ytsearch10:{query}"
        if is_playlist
        else f"ytsearch1:{query}"
    )

    # Spotify Resolver
    if "spotify.com" in query:

        opts = {
            "quiet": True,
            "format": "bestaudio/best",
            "noplaylist": True
        }

        try:

            with YoutubeDL(opts) as ydl:

                info = await asyncio.to_thread(
                    ydl.extract_info,
                    query,
                    download=False
                )

                search = (
                    f"ytsearch1:{info.get('title', 'song')}"
                )

        except Exception as e:

            logger.error(
                f"Spotify Resolve Fail: {e}"
            )

    ydl_opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "noplaylist": not is_playlist
    }

    try:

        with YoutubeDL(ydl_opts) as ydl:

            info = await asyncio.to_thread(
                ydl.extract_info,
                query if "http" in query else search,
                download=False
            )

        entries = info.get("entries") or [info]

        added = 0

        for entry in entries[:MAX_PLAYLIST_SIZE]:

            if not entry:
                continue

            data = {
                "title": entry.get(
                    "title",
                    "Unknown Song"
                ),
                "url": entry.get("url")
            }

            if not data["url"]:
                continue

            if not recovery:

                QUEUE[chat_id].append(data)

                async with aiosqlite.connect(
                    "ruhi_supreme.db"
                ) as db:

                    await db.execute(
                        "INSERT INTO p_queue VALUES (?, ?, ?)",
                        (
                            chat_id,
                            data["title"],
                            data["url"]
                        )
                    )

                    await db.commit()

            added += 1

        # Join VC
        if chat_id not in ACTIVE_CALLS:

            try:

                await call_py.join_group_call(
                    chat_id,
                    AudioPiped(
                        "https://raw.githubusercontent.com/TheHamkerCat/WilliamButcherBot/master/cache/empty.aac"
                    )
                )

                ACTIVE_CALLS.add(chat_id)

            except Exception as e:

                logger.error(
                    f"VC Join Error: {e}"
                )

                if msg:
                    await msg.edit(
                        "❌ VC Join Failed."
                    )

                return

        # Start Playback
        if len(QUEUE[chat_id]) <= added or seek > 0:

            await asyncio.sleep(2)

            asyncio.create_task(
                play_next(chat_id, seek=seek)
            )

        if msg:

            await msg.edit(
                f"🎵 Added {added} track(s)."
            )

    except Exception as e:

        logger.error(f"Play Fail: {e}")

        if msg:
            await msg.edit("❌ Load Failed.")


async def play_next(chat_id, seek=0):

    async with CHAT_LOCKS[chat_id]:

        if not QUEUE[chat_id]:

            with suppress(Exception):

                await call_py.leave_group_call(
                    chat_id
                )

            ACTIVE_CALLS.discard(chat_id)

            return

        song = QUEUE[chat_id][0]

        try:

            await call_py.change_stream(
                chat_id,
                AudioPiped(song["url"])
            )

            PLAY_START_TIME[chat_id] = (
                time.time() - seek
            )

            TTS_PLAYING[chat_id] = False

        except Exception as e:

            logger.error(
                f"Stream Fail: {e}"
            )

            if QUEUE[chat_id]:

                QUEUE[chat_id].pop(0)

            await asyncio.sleep(3)

            if QUEUE[chat_id]:

                asyncio.create_task(
                    play_next(chat_id)
                )


@call_py.on_stream_end()
async def on_end(_, update):

    try:

        chat_id = update.chat_id

        if QUEUE[chat_id]:

            old = QUEUE[chat_id].pop(0)

            await remove_song_db(
                chat_id,
                old["title"]
            )

            await asyncio.sleep(2)

            if QUEUE[chat_id]:

                asyncio.create_task(
                    play_next(chat_id)
                )

            else:

                with suppress(Exception):

                    await call_py.leave_group_call(
                        chat_id
                    )

                ACTIVE_CALLS.discard(chat_id)

    except Exception as e:

        logger.error(
            f"StreamEnd Error: {e}"
        )

#=========================================

#=========================================
#=========================================
#=========================================
# RAW VC LISTENER (AUTO FUTURE SUPPORT)
#=========================================

if hasattr(call_py, "on_raw_audio_received"):

    @call_py.on_raw_audio_received()
    async def on_voice_frame(_, frame):

        try:

            chat_id = frame.chat_id

            if (
                IS_PROCESSING[chat_id]
                or TTS_LOCK[chat_id].locked()
                or TTS_PLAYING[chat_id]
            ):
                return

            if not getattr(frame, "data", None):
                return

            audio_np = np.frombuffer(
                frame.data,
                dtype=np.int16
            )

            if len(audio_np) == 0:
                return

            energy = np.sqrt(
                np.mean(
                    audio_np.astype(
                        np.float32
                    ) ** 2
                )
            )

            # Voice Detected
            if energy > VAD_THRESHOLD:

                AUDIO_BUFFER[chat_id].append(
                    frame.data
                )

                SILENCE_COUNT[chat_id] = 0

                if (
                    len(AUDIO_BUFFER[chat_id])
                    > MAX_BUFFER_FRAMES
                ):

                    AUDIO_BUFFER[chat_id].pop(0)

            else:

                SILENCE_COUNT[chat_id] += 1

            # Fast Speech Processing
            if (
                SILENCE_COUNT[chat_id] > 10
                and len(AUDIO_BUFFER[chat_id]) > 20
            ):

                data = b"".join(
                    AUDIO_BUFFER[chat_id]
                )

                AUDIO_BUFFER[chat_id].clear()

                SILENCE_COUNT[chat_id] = 0

                asyncio.create_task(
                    process_voice(
                        chat_id,
                        data,
                        getattr(
                            frame,
                            "user_id",
                            0
                        )
                    )
                )

        except Exception as e:

            logger.error(
                f"Voice Frame Error: {e}"
            )

else:

    logger.warning(
        "⚠ Raw VC listener unsupported in current PyTgCalls build."
    )
#=========================================

#=========================================

#=========================================
#=========================================
# VOICE MESSAGE AI + VC TALK SYSTEM
#=========================================

@bot.on_message(filters.voice)
async def voice_message_ai(_, m: Message):

    if not m.voice:
        return

    if not m.from_user:
        return

    chat_id = m.chat.id
    user_id = m.from_user.id

    try:

        status = await m.reply(
            "🎤 Listening..."
        )

        voice_file = await m.download(
            file_name=f"v_{uuid.uuid4().hex}.ogg"
        )

        # Speech To Text
        segs, _ = await asyncio.to_thread(
            whisper_model.transcribe,
            voice_file,
            language="hi"
        )

        text = "".join(
            [s.text for s in segs]
        ).strip().lower()

        if not text:

            with suppress(Exception):
                os.remove(voice_file)

            return await status.edit(
                "❌ Kuch samajh nahi aya."
            )

        clean = text.strip()

        # Wake Word Check
        if not any(w in clean for w in WAKE_WORDS):

            with suppress(Exception):
                os.remove(voice_file)

            return

        for w in WAKE_WORDS:

            clean = clean.replace(
                w,
                ""
            ).strip()

        # Cooldown
        now = time.time()

        if now - AI_COOLDOWN[user_id] < 3:

            with suppress(Exception):
                os.remove(voice_file)

            return await status.edit(
                "⏳ Wait..."
            )

        AI_COOLDOWN[user_id] = now

        # PLAY SONG
        if clean.startswith("play "):

            with suppress(Exception):
                os.remove(voice_file)

            return await handle_play(
                chat_id,
                clean.replace(
                    "play",
                    "",
                    1
                ).strip(),
                status
            )

        # STOP MUSIC
        if "stop" in clean:

            QUEUE[chat_id].clear()

            await clear_queue_db(chat_id)

            with suppress(Exception):

                await call_py.leave_group_call(
                    chat_id
                )

            ACTIVE_CALLS.discard(
                chat_id
            )

            with suppress(Exception):
                os.remove(voice_file)

            return await status.edit(
                "⏹ Stopped"
            )

        # PAUSE MUSIC
        if "pause" in clean:

            with suppress(Exception):

                await call_py.pause_stream(
                    chat_id
                )

            with suppress(Exception):
                os.remove(voice_file)

            return await status.edit(
                "⏸ Paused"
            )

        # RESUME MUSIC
        if "resume" in clean:

            with suppress(Exception):

                await call_py.resume_stream(
                    chat_id
                )

            with suppress(Exception):
                os.remove(voice_file)

            return await status.edit(
                "▶️ Resumed"
            )

        # AI CHAT REPLY
        try:

            res = await asyncio.to_thread(
                ai_model.generate_content,
                f"Reply naturally in Hinglish: {clean}"
            )

            ans = (
                res.text.strip()[:400]
                if hasattr(res, "text")
                else "Boliye 🙂"
            )

        except Exception as e:

            logger.error(
                f"Voice AI Error: {e}"
            )

            ans = "Network issue 😭"

        await status.edit(
            f"🧠 {ans}"
        )

        # MEMORY
        CHAT_MEMORY[chat_id].append(
            f"U:{clean[:120]} | R:{ans[:200]}"
        )

        asyncio.create_task(
            save_chat_memory(chat_id)
        )

        # SPEAK IN VC
        if chat_id in ACTIVE_CALLS:

            seek_pos = (
                int(
                    time.time()
                    - PLAY_START_TIME[chat_id]
                ) + 2
                if chat_id in PLAY_START_TIME
                else 0
            )

            async with TTS_LOCK[chat_id]:

                TTS_PLAYING[chat_id] = True

                tts_file = (
                    f"tts_{uuid.uuid4().hex}.mp3"
                )

                try:

                    await edge_tts.Communicate(
                        ans,
                        VOICE
                    ).save(tts_file)

                    await call_py.change_stream(
                        chat_id,
                        AudioPiped(tts_file)
                    )

                    await asyncio.sleep(
                        max(
                            3,
                            len(ans.split()) // 3
                        )
                    )

                    # Resume Music
                    if QUEUE.get(chat_id):

                        await play_next(
                            chat_id,
                            seek=seek_pos
                        )

                except Exception as e:

                    logger.error(
                        f"VC Voice Reply Error: {e}"
                    )

                finally:

                    TTS_PLAYING[chat_id] = False

                    with suppress(Exception):

                        os.remove(tts_file)

        with suppress(Exception):

            os.remove(voice_file)

    except Exception as e:

        logger.error(
            f"Voice Message Handler Error: {e}"
        )

        await m.reply(
            "❌ Voice processing failed."
        )
# =========================================
# 7.5 TEXT COMMAND DISPATCHER (FIXED & SYNCED)
# =========================================

@bot.on_message(filters.command(["start", "play", "volume", "quiz", "truth", "dare", "help", "skip", "stop", "join", "queue", "ttt", "pause", "resume"]) & filters.incoming)
async def dispatcher(_, m: Message):
    if not m.from_user: 
        return
    
    chat_id = m.chat.id
    cmd = m.command[0].lower()
    user_id = m.from_user.id

    # --- ADMIN CHECK (Only for Groups) ---
    admin_cmds = ["play", "skip", "stop", "join", "volume", "pause", "resume"]
    if cmd in admin_cmds and m.chat.type != m.chat.type.PRIVATE:
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                return await m.reply("❌ Sirf Admins ye command chala sakte hain.")
        except Exception as e:
            logger.error(f"Admin Check Error: {e}")

    # --- COMMANDS LOGIC ---
    
    if cmd == "start":
        await m.reply("✨ **Ruhi Supreme 5.6 Online**\nBulletproof Build! 🚀\n\nCommands dekhne ke liye /help likho.")

    elif cmd == "help":
        await m.reply("📚 **Ruhi Supreme Commands:**\n\n🎵 **Music:** /play, /skip, /stop, /pause, /resume, /queue, /volume, /join\n🎮 **Games:** /ttt, /quiz, /truth, /dare")

    elif cmd == "play":
        query = " ".join(m.command[1:]).strip()
        if not query:
            return await m.reply("🎵 Gaane ka naam ya link toh do bhai.")
        
        # Cooldown check
        now = time.time()
        if now - PLAY_COOLDOWN[chat_id] < 3:
            return await m.reply("⏳ Sabar karo, 3 second ruko.")
        
        PLAY_COOLDOWN[chat_id] = now
        status = await m.reply("🔍 Searching...")
        await handle_play(chat_id, query, status)

    elif cmd == "stop":
        QUEUE[chat_id].clear()
        await clear_queue_db(chat_id)
        with suppress(Exception):
            await call_py.leave_group_call(chat_id)
        ACTIVE_CALLS.discard(chat_id)
        await m.reply("⏹ Music band aur Queue saaf kar di hai.")

    elif cmd == "skip":
        if not QUEUE[chat_id]:
            return await m.reply("📭 Queue mein kuch hai hi nahi skip karne ko.")
        
        old = QUEUE[chat_id].pop(0)
        await remove_song_db(chat_id, old["title"])
        await asyncio.sleep(1)
        asyncio.create_task(play_next(chat_id))
        await m.reply(f"⏭ Skipped: **{old['title']}**")

    elif cmd == "queue":
        if not QUEUE[chat_id]:
            return await m.reply("📭 Queue khali hai.")
        
        text = "🎶 **Current Queue:**\n"
        for i, song in enumerate(QUEUE[chat_id][:10], start=1):
            text += f"{i}. {song['title']}\n"
        await m.reply(text)

    elif cmd == "join":
        if chat_id in ACTIVE_CALLS:
            return await m.reply("🎙 Main pehle se VC mein hu.")
        try:
            await call_py.join_group_call(chat_id, AudioPiped("https://raw.githubusercontent.com/TheHamkerCat/WilliamButcherBot/master/cache/empty.aac"))
            ACTIVE_CALLS.add(chat_id)
            await m.reply("🎙 VC Join kar liya hai!")
        except NoActiveGroupCall:
            await m.reply("❌ Pehle Group mein Video Chat start karo.")
        except Exception as e:
            logger.error(f"Join Fail: {e}")

    elif cmd == "volume":
        if len(m.command) < 2:
            return await m.reply("Usage: /volume 0-200")
        try:
            vol = int(m.command[1])
            VOLUME[chat_id] = max(0, min(200, vol))
            await m.reply(f"🔊 Volume set to: {VOLUME[chat_id]}%")
        except:
            await m.reply("❌ Sahi number daalo (0-200).")

    elif cmd == "pause":
        with suppress(Exception):
            await call_py.pause_stream(chat_id)
        await m.reply("⏸ Paused.")

    elif cmd == "resume":
        with suppress(Exception):
            await call_py.resume_stream(chat_id)
        await m.reply("▶️ Resumed.")

    elif cmd == "quiz":
        try:
            prompt = "Generate 1 difficult NEET MCQ. Format: Question|OptA|OptB|OptC|OptD|CorrectLetter"
            res = (await asyncio.to_thread(ai_model.generate_content, prompt)).text.split("|")
            if len(res) >= 6:
                QUIZ_DATA[chat_id] = res[5].strip().upper()
                buttons = [[InlineKeyboardButton(res[i+1].strip(), callback_data=f"qz_{chr(65+i)}")] for i in range(4)]
                await m.reply(f"📖 **Quiz:** {res[0]}", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            logger.error(f"Quiz Error: {e}")
            await m.reply("❌ Quiz nahi ban paya, firse try karo.")

    elif cmd == "ttt":
        GAME_STATE[chat_id] = [""] * 9
        await m.reply("🎮 **Tic-Tac-Toe Shuru!**", reply_markup=get_ttt_kb(chat_id))

    elif cmd == "truth":
        await m.reply(f"🤔 **Truth:** {random.choice(['Apna sabse bada secret batao?', 'Kisi par crush hai?', 'Akhri baar jhoot kab bola?', 'Zindagi ka sabse embarrassing moment?'])}")

    elif cmd == "dare":
        await m.reply(f"🔥 **Dare:** {random.choice(['Ek gaana gaao aur voice note bhejo.', 'Apne crush ko message karo.', '10 pushups maaro video mein (ya sach bolo).', 'Apni sabse purani photo dikhao.'])}")


#=========================================
#8. CALLBACKS & WATCHDOG (FINAL FIXED)
#=========================================

@bot.on_callback_query(
    filters.regex("^(ttt_|qz_)")
)
async def cb_router(_, cb: CallbackQuery):

    try:

        if not cb.message:
            return

        chat_id = cb.message.chat.id
        now = time.time()

        # Cooldown
        if now - CB_COOLDOWN[chat_id] < 1:

            return await cb.answer(
                "Sabar! ⏳",
                show_alert=False
            )

        CB_COOLDOWN[chat_id] = now

        # RESET GAME
        if cb.data == "ttt_reset":

            GAME_STATE[chat_id] = [""] * 9

            with suppress(Exception):

                return await cb.edit_message_text(
                    "🎮 Reset!",
                    reply_markup=get_ttt_kb(chat_id)
                )

        # QUIZ CALLBACK
        if cb.data.startswith("qz_"):

            answer = cb.data.split("_")[1]

            if answer == QUIZ_DATA.get(chat_id):

                await update_score(
                    cb.from_user.id
                )

                with suppress(Exception):

                    await cb.edit_message_text(
                        "✅ Correct Answer!"
                    )

            else:

                await cb.answer(
                    "❌ Galat!",
                    show_alert=True
                )

        # TIC TAC TOE CALLBACK
        elif cb.data.startswith("ttt_"):

            idx = int(
                cb.data.split("_")[1]
            )

            if not GAME_STATE[chat_id][idx]:

                # User Move
                GAME_STATE[chat_id][idx] = "❌"

                result = check_ttt_winner(
                    GAME_STATE[chat_id]
                )

                # Bot Move
                if not result:

                    bot_idx = smart_ttt_move(
                        GAME_STATE[chat_id]
                    )

                    if bot_idx is not None:

                        GAME_STATE[chat_id][bot_idx] = "⭕"

                    result = check_ttt_winner(
                        GAME_STATE[chat_id]
                    )

                # End Game
                if result:

                    with suppress(Exception):

                        await cb.edit_message_text(
                            f"🏁 Winner: {result}",
                            reply_markup=get_ttt_kb(chat_id)
                        )

                    GAME_STATE.pop(
                        chat_id,
                        None
                    )

                else:

                    with suppress(Exception):

                        await cb.edit_message_text(
                            "🎮 Game On:",
                            reply_markup=get_ttt_kb(chat_id)
                        )

    except Exception as e:

        logger.error(
            f"Callback Error: {e}"
        )


#=========================================
# WATCHDOG
#=========================================

async def watchdog():

    while True:

        try:

            await asyncio.sleep(60)

            # Assistant Reconnect
            if not getattr(
                assistant,
                "is_connected",
                False
            ):

                try:

                    await assistant.connect()

                    logger.info(
                        "Assistant Reconnected"
                    )

                except Exception as e:

                    logger.error(
                        f"Assistant reconnect fail: {e}"
                    )

            # Active Calls Check
            for chat_id in list(ACTIVE_CALLS):

                try:

                    call = await call_py.get_call(
                        chat_id
                    )

                    status = str(
                        getattr(call, "status", "")
                    ).lower()

                    if (
                        "playing" not in status
                        and "paused" not in status
                    ):

                        ACTIVE_CALLS.discard(
                            chat_id
                        )

                except Exception:

                    ACTIVE_CALLS.discard(
                        chat_id
                    )

        except Exception as e:

            logger.error(
                f"Watchdog Error: {e}"
            )

            await asyncio.sleep(5)
#=========================================

#=========================================
#=========================================
#9. MAIN (FINAL FIXED)
#=========================================

async def main():

    # Init DB + Load Memory
    await init_db()
    await load_memories()

    # Cleanup temp files
    for f in os.listdir():

        if (
            f.startswith("v_")
            or f.startswith("tts_")
        ):

            with suppress(Exception):

                os.remove(f)

    try:

        print("🚀 Starting Ruhi Supreme...")

        # Start Bot
        await bot.start()

        print("✅ Bot Started")

        # Start Assistant
        await assistant.start()

        print("✅ Assistant Started")

        # Start PyTgCalls
        await call_py.start()

        print("✅ PyTgCalls Started")

        # Background Tasks
        asyncio.create_task(
            recover_queue()
        )

        asyncio.create_task(
            watchdog()
        )

        print(
            "👑 RUHI SUPREME 5.6 FINAL MASTER BUILD LIVE"
        )

        # Keep Alive
        await idle()

    except Exception as e:

        logger.exception(
            f"Startup Error: {e}"
        )

    finally:

        print("🛑 Stopping Ruhi Supreme...")

        with suppress(Exception):

            await call_py.stop()

        with suppress(Exception):

            await assistant.stop()

        with suppress(Exception):

            await bot.stop()

        print("✅ Shutdown Complete")


#=========================================
# RUN BOT
#=========================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print("🛑 Bot Stopped By User")