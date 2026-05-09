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
# 1. ULTIMATE CONFIG & GLOBALS
# =========================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
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
WAKE_WORDS = ["ruhi", "roohi"]
VOICE = "hi-IN-SwaraNeural"

#AI Models

print("🚀 Loading Ruhi Supreme 5.6: Bulletproof Final Build...")
whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel("gemini-1.5-flash")

bot = Client("RuhiBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
assistant = Client("RuhiAssistant", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
call_py = PyTgCalls(assistant)

# States (Indestructible)

QUEUE = defaultdict(list)
ACTIVE_CALLS = set()
AUDIO_BUFFER = defaultdict(list)
CHAT_LOCKS = defaultdict(Lock)
TTS_LOCK = defaultdict(Lock)
VOICE_LOCK = defaultdict(Lock)
CPU_SHIELD = Semaphore(3)
IS_PROCESSING = defaultdict(bool)
TTS_PLAYING = defaultdict(bool)
SILENCE_COUNT = defaultdict(int)
VOLUME = defaultdict(lambda: 100)
PLAY_START_TIME = defaultdict(float)
GAME_STATE = {}
QUIZ_DATA = {}
CHAT_MEMORY = defaultdict(lambda: deque(maxlen=5))
AI_COOLDOWN = defaultdict(lambda: 0)
CB_COOLDOWN = defaultdict(lambda: 0)
PLAY_COOLDOWN = defaultdict(lambda: 0)

#=========================================

# =========================================
# 2. DATABASE & PERSISTENCE
# =========================================

async def init_db():
    async with aiosqlite.connect("ruhi_supreme.db") as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS stats (user_id INTEGER PRIMARY KEY, score INTEGER DEFAULT 0)"
        )

        await db.execute(
            "CREATE TABLE IF NOT EXISTS memory (chat_id INTEGER PRIMARY KEY, context TEXT)"
        )

        await db.execute(
            "CREATE TABLE IF NOT EXISTS p_queue (chat_id INTEGER, title TEXT, url TEXT)"
        )

        await db.commit()


async def update_score(user_id):
    async with aiosqlite.connect("ruhi_supreme.db") as db:

        await db.execute(
            "INSERT OR REPLACE INTO stats (user_id, score) VALUES (?, COALESCE((SELECT score FROM stats WHERE user_id = ?), 0) + 1)",
            (user_id, user_id)
        )

        await db.commit()


async def save_chat_memory(chat_id):

    context = json.dumps(list(CHAT_MEMORY[chat_id]))

    async with aiosqlite.connect("ruhi_supreme.db") as db:

        await db.execute(
            "INSERT OR REPLACE INTO memory VALUES (?, ?)",
            (chat_id, context)
        )

        await db.commit()


async def load_memories():

    async with aiosqlite.connect("ruhi_supreme.db") as db:

        async with db.execute("SELECT * FROM memory") as cursor:

            async for row in cursor:

                if row[1]:

                    try:
                        CHAT_MEMORY[row[0]] = deque(
                            json.loads(row[1]),
                            maxlen=5
                        )

                    except Exception as e:
                        logger.error(f"Memory Load Error: {e}")


async def remove_song_db(chat_id, title):

    async with aiosqlite.connect("ruhi_supreme.db") as db:

        await db.execute(
            "DELETE FROM p_queue WHERE chat_id = ? AND title = ?",
            (chat_id, title)
        )

        await db.commit()


async def clear_queue_db(chat_id):

    async with aiosqlite.connect("ruhi_supreme.db") as db:

        await db.execute(
            "DELETE FROM p_queue WHERE chat_id = ?",
            (chat_id,)
        )

        await db.commit()
#=========================================

# =========================================
# 3. QUEUE RECOVERY (FIX 2 Applied)
# =========================================

async def recover_queue():

    await asyncio.sleep(5)

    async with aiosqlite.connect("ruhi_supreme.db") as db:

        async with db.execute("SELECT * FROM p_queue") as cursor:

            async for row in cursor:

                chat_id, title, url = row

                if not any(x["url"] == url for x in QUEUE[chat_id]):

                    QUEUE[chat_id].append({
                        "title": title,
                        "url": url
                    })

    for chat_id in list(QUEUE.keys()):

        if chat_id not in ACTIVE_CALLS:

            try:

                await call_py.join_group_call(
                    chat_id,
                    AudioPiped(
                        "https://raw.githubusercontent.com/TheHamkerCat/WilliamButcherBot/master/cache/empty.aac"
                    )
                )

                ACTIVE_CALLS.add(chat_id)

                await asyncio.sleep(1)

                # Improvement: Avoid duplicate tasks if QUEUE is populated
                if QUEUE[chat_id]:

                    asyncio.create_task(
                        play_next(chat_id)
                    )

            except Exception as e:

                logger.error(
                    f"Recovery Fail in {chat_id}: {e}"
                )

#=========================================

#=========================================
#4. GAMES LOGIC
#=========================================

def smart_ttt_move(board):

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

    for char in ["⭕", "❌"]:

        for a, b, c in ws:

            line = [board[a], board[b], board[c]]

            if line.count(char) == 2 and line.count("") == 1:
                return [a, b, c][line.index("")]

    if board[4] == "":
        return 4

    empty = [i for i, v in enumerate(board) if not v]

    return random.choice(empty) if empty else None


def get_ttt_kb(chat_id):

    b = GAME_STATE.get(chat_id, [""] * 9)

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

    kb.append([
        InlineKeyboardButton(
            "Reset 🔄",
            callback_data="ttt_reset"
        )
    ])

    return InlineKeyboardMarkup(kb)


def check_ttt_winner(board):

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

        if board[a] == board[b] == board[c] != "":
            return board[a]

    return "Draw" if "" not in board else None
#=========================================

#=========================================
#5. MUSIC ENGINE (FIX 1 Applied)
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

                search = f"ytsearch1:{info.get('title', 'song')}"

        except Exception as e:

            logger.error(f"Spotify Resolve Fail: {e}")

    ydl_opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "noplaylist": not is_playlist
    }

    with YoutubeDL(ydl_opts) as ydl:

        try:

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

                    logger.error(f"VC Join Error: {e}")

            # Start Playback
            if len(QUEUE[chat_id]) <= added or seek > 0:

                await asyncio.sleep(1)

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
                await call_py.leave_group_call(chat_id)

            ACTIVE_CALLS.discard(chat_id)

            return

        song = QUEUE[chat_id][0]

        try:

            ffmpeg_params = (
                "-reconnect 1 "
                "-reconnect_streamed 1 "
                "-reconnect_delay_max 5 "
                f"-vn -filter:a volume={VOLUME[chat_id] / 100}"
            )

            if seek > 0:
                ffmpeg_params += f" -ss {seek}"

            await call_py.change_stream(
                chat_id,
                AudioPiped(
                    song["url"],
                    ffmpeg_parameters=ffmpeg_params
                )
            )

            PLAY_START_TIME[chat_id] = (
                time.time() - seek
            )

            TTS_PLAYING[chat_id] = False

        except Exception as e:

            logger.error(f"Stream Fail: {e}")

            if QUEUE[chat_id]:
                QUEUE[chat_id].pop(0)

            await asyncio.sleep(1)

            asyncio.create_task(
                play_next(chat_id)
            )


@call_py.on_stream_end
async def on_end(_, update: StreamAudioEnded):

    chat_id = update.chat_id

    if QUEUE[chat_id]:

        old = QUEUE[chat_id].pop(0)

        await remove_song_db(
            chat_id,
            old["title"]
        )

        await asyncio.sleep(1)

        asyncio.create_task(
            play_next(chat_id)
        )

#=========================================

#=========================================
#6. VOICE ENGINE
#=========================================

async def process_voice(chat_id, raw_bytes, user_id):

    async with CPU_SHIELD, VOICE_LOCK[chat_id]:

        IS_PROCESSING[chat_id] = True

        try:

            audio_int16 = np.frombuffer(
                raw_bytes,
                dtype=np.int16
            )

            audio_float32 = np.interp(
                np.linspace(
                    0,
                    len(audio_int16),
                    int(len(audio_int16) * 16000 / 48000),
                    endpoint=False
                ),
                np.arange(len(audio_int16)),
                audio_int16
            ).astype(np.float32) / 32768.0

            segs, _ = await asyncio.to_thread(
                whisper_model.transcribe,
                audio_float32,
                language="hi"
            )

            text = "".join(
                [s.text for s in segs]
            ).strip().lower()

            if len(text.split()) < 2 or len(text) < 5:
                return

            if not any(w in text for w in WAKE_WORDS):
                return

            clean = text

            for w in WAKE_WORDS:
                clean = clean.replace(w, "").strip()

            now = time.time()

            if now - AI_COOLDOWN[user_id] < 5:
                return

            AI_COOLDOWN[user_id] = now

            # Voice Play Command
            if clean.startswith("play "):

                return await handle_play(
                    chat_id,
                    clean.replace("play", "", 1).strip()
                )

            # Voice Stop Command
            if "stop" in clean:

                QUEUE[chat_id].clear()

                await clear_queue_db(chat_id)

                with suppress(Exception):
                    await call_py.leave_group_call(chat_id)

                ACTIVE_CALLS.discard(chat_id)

                return

            # Resume Position
            seek_pos = (
                int(time.time() - PLAY_START_TIME[chat_id]) + 2
                if chat_id in PLAY_START_TIME
                else 0
            )

            # AI Reply
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

                logger.error(f"AI Gen Error: {e}")

                ans = "Network issue 😭"

            # Save Memory
            CHAT_MEMORY[chat_id].append(
                f"U:{clean[:120]} | R:{ans[:200]}"
            )

            asyncio.create_task(
                save_chat_memory(chat_id)
            )

            # TTS Reply
            async with TTS_LOCK[chat_id]:

                TTS_PLAYING[chat_id] = True

                file = f"v_{uuid.uuid4().hex}.mp3"

                try:

                    await edge_tts.Communicate(
                        ans,
                        VOICE
                    ).save(file)

                    await call_py.change_stream(
                        chat_id,
                        AudioPiped(file)
                    )

                    await asyncio.sleep(
                        max(3, len(ans.split()) // 3)
                    )

                    if QUEUE.get(chat_id):

                        await asyncio.sleep(1)

                        await play_next(
                            chat_id,
                            seek=seek_pos
                        )

                except Exception as e:

                    logger.error(f"TTS Error: {e}")

                finally:

                    TTS_PLAYING[chat_id] = False

                    with suppress(Exception):
                        os.remove(file)

        except Exception as e:

            logger.error(
                f"Voice Processor Error: {e}"
            )

        finally:

            IS_PROCESSING[chat_id] = False


@call_py.on_raw_audio_received
async def on_voice_frame(_, frame: AudioFrame):

    chat_id = frame.chat_id

    if (
        IS_PROCESSING[chat_id]
        or TTS_LOCK[chat_id].locked()
        or TTS_PLAYING[chat_id]
    ):
        return

    audio_np = np.frombuffer(
        frame.data,
        dtype=np.int16
    )

    if len(audio_np) == 0:
        return

    energy = np.sqrt(
        np.mean(
            audio_np.astype(np.float32) ** 2
        )
    )

    # Voice Detected
    if energy > VAD_THRESHOLD:

        AUDIO_BUFFER[chat_id].append(frame.data)

        SILENCE_COUNT[chat_id] = 0

        if len(AUDIO_BUFFER[chat_id]) > MAX_BUFFER_FRAMES:

            AUDIO_BUFFER[chat_id].pop(0)

    else:

        SILENCE_COUNT[chat_id] += 1

    # Process Speech
    if (
        SILENCE_COUNT[chat_id] > 20
        and len(AUDIO_BUFFER[chat_id]) > 40
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
                getattr(frame, "user_id", 0)
            )
        )

#=========================================

#=========================================

#=========================================
#7. DISPATCHER & COMMANDS
#=========================================

@bot.on_message(
    filters.command([
        "start",
        "play",
        "volume",
        "quiz",
        "truth",
        "dare",
        "help",
        "skip",
        "stop",
        "join",
        "queue",
        "ttt",
        "pause",
        "resume"
    ])
)
async def dispatcher(_, m: Message):

    if not m.from_user:
        return

    chat_id = m.chat.id
    cmd = m.command[0].lower()

    admin_cmds = [
        "play",
        "skip",
        "stop",
        "join",
        "volume",
        "pause",
        "resume"
    ]

    # Admin Check
    if cmd in admin_cmds:

        try:

            member = await bot.get_chat_member(
                chat_id,
                m.from_user.id
            )

            if member.status not in [
                ChatMemberStatus.OWNER,
                ChatMemberStatus.ADMINISTRATOR
            ]:

                return await m.reply(
                    "❌ Admin Only."
                )

        except Exception as e:

            logger.error(
                f"Admin Check Error: {e}"
            )

            return await m.reply(
                "❌ Admin check failed."
            )

    # HELP
    if cmd == "help":

        await m.reply(
            "📚 **Ruhi Commands:**\n"
            "/play /skip /stop /queue\n"
            "/volume /join /quiz /ttt\n"
            "/truth /dare /pause /resume"
        )

    # QUEUE
    elif cmd == "queue":

        if not QUEUE[chat_id]:

            return await m.reply(
                "📭 Queue empty."
            )

        text = "🎶 **Queue:**\n"

        for i, song in enumerate(
            QUEUE[chat_id][:10],
            start=1
        ):

            text += f"{i}. {song['title']}\n"

        await m.reply(text)

    # TRUTH
    elif cmd == "truth":

        await m.reply(
            random.choice([
                "🤔 Biggest secret?",
                "🤔 Crush?",
                "🤔 Last lie?"
            ])
        )

    # DARE
    elif cmd == "dare":

        await m.reply(
            random.choice([
                "🔥 Gaana gao.",
                "🔥 10 pushups.",
                "🔥 Voice note bhejo."
            ])
        )

    # START
    elif cmd == "start":

        await m.reply(
            "✨ **Ruhi Supreme 5.6 Online**\n"
            "Bulletproof Build! 🚀"
        )

    # JOIN VC
    elif cmd == "join":

        if chat_id in ACTIVE_CALLS:

            return await m.reply(
                "🎙 Already in VC."
            )

        try:

            await call_py.join_group_call(
                chat_id,
                AudioPiped(
                    "https://raw.githubusercontent.com/TheHamkerCat/WilliamButcherBot/master/cache/empty.aac"
                )
            )

            ACTIVE_CALLS.add(chat_id)

            await m.reply(
                "🎙 Joined VC."
            )

        except NoActiveGroupCall:

            await m.reply(
                "❌ VC start karo pehle."
            )

        except Exception as e:

            logger.error(f"Join Fail: {e}")

    # PLAY
    elif cmd == "play":

        query = " ".join(
            m.command[1:]
        ).strip()

        if not query:

            return await m.reply(
                "🎵 Song name do."
            )

        now = time.time()

        if now - PLAY_COOLDOWN[chat_id] < 3:

            return await m.reply(
                "⏳ Wait..."
            )

        PLAY_COOLDOWN[chat_id] = now

        await handle_play(
            chat_id,
            query,
            await m.reply("🔍 Searching...")
        )

    # VOLUME
    elif cmd == "volume":

        if len(m.command) < 2:

            return await m.reply(
                "Usage: /volume 0-200"
            )

        try:

            vol = int(m.command[1])

            VOLUME[chat_id] = max(
                0,
                min(200, vol)
            )

            await m.reply(
                f"🔊 Vol: {VOLUME[chat_id]}%"
            )

        except Exception as e:

            logger.error(
                f"Volume Error: {e}"
            )

            return await m.reply(
                "❌ Number do."
            )

    # PAUSE
    elif cmd == "pause":

        with suppress(Exception):

            await call_py.pause_stream(chat_id)

        await m.reply("⏸ Paused")

    # RESUME
    elif cmd == "resume":

        with suppress(Exception):

            await call_py.resume_stream(chat_id)

        await m.reply("▶️ Resumed")

    # QUIZ
    elif cmd == "quiz":

        try:

            res = (
                await asyncio.to_thread(
                    ai_model.generate_content,
                    "Generate 1 NEET MCQ. Question|A|B|C|D|CorrectLetter"
                )
            ).text.split("|")

            if len(res) >= 6:

                QUIZ_DATA[chat_id] = (
                    res[5].strip().upper()
                )

                kb = [
                    [
                        InlineKeyboardButton(
                            res[i + 1].strip(),
                            callback_data=f"qz_{chr(65+i)}"
                        )
                    ]
                    for i in range(4)
                ]

                await m.reply(
                    f"📖 **Quiz:** {res[0]}",
                    reply_markup=InlineKeyboardMarkup(kb)
                )

        except Exception as e:

            logger.error(
                f"Quiz Gen Fail: {e}"
            )

            await m.reply(
                "❌ Quiz failed."
            )

    # TIC TAC TOE
    elif cmd == "ttt":

        GAME_STATE[chat_id] = [""] * 9

        await m.reply(
            "🎮 **TicTacToe!**",
            reply_markup=get_ttt_kb(chat_id)
        )

    # SKIP
    elif cmd == "skip":

        if QUEUE[chat_id]:

            old = QUEUE[chat_id].pop(0)

            await remove_song_db(
                chat_id,
                old["title"]
            )

            await asyncio.sleep(1)

            await play_next(chat_id)

            await m.reply(
                "⏭ Skipped"
            )

    # STOP
    elif cmd == "stop":

        QUEUE[chat_id].clear()

        await clear_queue_db(chat_id)

        with suppress(Exception):

            await call_py.leave_group_call(
                chat_id
            )

        ACTIVE_CALLS.discard(chat_id)

        await m.reply(
            "⏹ Stopped"
        )
#=========================================

#=========================================
#8. CALLBACKS & WATCHDOG
#=========================================

@bot.on_callback_query(
    filters.regex("^(ttt_|qz_)")
)
async def cb_router(_, cb: CallbackQuery):

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

                await cb.edit_message_text(
                    f"🏁 Winner: {result}",
                    reply_markup=get_ttt_kb(chat_id)
                )

                GAME_STATE.pop(
                    chat_id,
                    None
                )

            else:

                await cb.edit_message_text(
                    "🎮 Game On:",
                    reply_markup=get_ttt_kb(chat_id)
                )


#=========================================
# WATCHDOG
#=========================================

async def watchdog():

    while True:

        await asyncio.sleep(60)

        try:

            # Assistant Reconnect
            if not getattr(
                assistant,
                "is_connected",
                False
            ):

                try:

                    await assistant.connect()

                except Exception as e:

                    logger.error(
                        f"Assistant reconnect fail: {e}"
                    )

            # Active Calls Check
            for chat_id in list(ACTIVE_CALLS):

                with suppress(Exception):

                    call = await call_py.get_call(
                        chat_id
                    )

                    status = str(
                        call.status
                    ).lower()

                    if (
                        "playing" not in status
                        and "paused" not in status
                    ):

                        ACTIVE_CALLS.discard(
                            chat_id
                        )

        except Exception as e:

            logger.error(
                f"Watchdog Error: {e}"
            )
#=========================================

#=========================================
#9. MAIN
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

        # Start Clients
        await bot.start()

        await assistant.start()

        await call_py.start()

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

        await idle()

    except Exception as e:

        logger.error(
            f"Startup Error: {e}"
        )

    finally:

        with suppress(Exception):

            await call_py.stop()

        with suppress(Exception):

            await assistant.stop()

        with suppress(Exception):

            await bot.stop()


#=========================================
# RUN BOT
#=========================================

if __name__ == "__main__":

    asyncio.run(main())