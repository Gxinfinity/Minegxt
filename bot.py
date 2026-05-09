import os
import re
import uuid
import random
import asyncio
import logging
import aiosqlite
import time
import json
import html
import subprocess
import urllib.parse
import urllib.request
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
from pyrogram.enums import ChatMemberStatus , ChatType
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

API_ID = int(os.getenv("API_ID", "33745438"))
API_HASH = os.getenv("API_HASH", "142eb5aab37976e2d39475b07e8e3212")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

LOGGER_ID = int(os.getenv("LOGGER_ID", "-1003009782265"))

VAD_THRESHOLD = 700
MAX_BUFFER_FRAMES = 250
MAX_PLAYLIST_SIZE = 15
MAX_QUEUE_LIMIT = 50

WAKE_WORDS = [
    "ruhi",
    "roohi"
]

DEFAULT_VOICE = os.getenv("RUHI_DEFAULT_VOICE", "hi-IN-SwaraNeural")

LANGUAGE_VOICES = {
    "hi": "hi-IN-SwaraNeural",
    "hinglish": "hi-IN-SwaraNeural",
    "ur": "ur-PK-UzmaNeural",
    "en": "en-IN-NeerjaNeural",
    "english": "en-IN-NeerjaNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "ar": "ar-SA-ZariyahNeural",
}

SEARCH_RESULT_LIMIT = 5

EMPTY_AUDIO = "https://raw.githubusercontent.com/TheHamkerCat/WilliamButcherBot/master/cache/empty.aac"

SUPPORTED_MUSIC_PLATFORMS = {
    "youtube.com",
    "youtu.be",
    "music.youtube.com",
    "soundcloud.com",
    "spotify.com",
    "open.spotify.com",
    "music.apple.com",
    "deezer.com",
    "jiosaavn.com",
    "saavn.com",
    "bandcamp.com",
}

METADATA_ONLY_MUSIC_DOMAINS = (
    "spotify.com",
    "open.spotify.com",
    "music.apple.com",
    "deezer.com",
    "jiosaavn.com",
    "saavn.com",
)

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

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

ai_model = genai.GenerativeModel("gemini-1.5-flash") if GEMINI_API_KEY else None

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

CHAT_VOICE = defaultdict(
    lambda: DEFAULT_VOICE
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

AUTO_PAUSED = defaultdict(bool)
#=========================================

# =========================================
# SHARED HELPERS
# =========================================

def get_chat_voice(chat_id):
    return CHAT_VOICE[chat_id]


async def safe_status(message, text):
    if not message:
        return

    for method in ("edit_text", "edit", "reply"):
        fn = getattr(message, method, None)
        if not fn:
            continue
        with suppress(Exception):
            await fn(text)
            return


def ensure_ai_ready():
    return ai_model is not None


async def generate_ai_text(prompt, fallback="Ji, boliye?"):
    if not ensure_ai_ready():
        return fallback

    try:
        response = await asyncio.to_thread(ai_model.generate_content, prompt)
        return response.text.strip() if hasattr(response, "text") and response.text else fallback
    except Exception as e:
        logger.error(f"AI Generate Error: {e}")
        return fallback


def _duckduckgo_search_sync(query, limit=SEARCH_RESULT_LIMIT):
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 RuhiBot/1.0"}
    )

    with urllib.request.urlopen(req, timeout=12) as response:
        page = response.read().decode("utf-8", errors="ignore")

    results = []
    pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        re.I | re.S
    )

    for href, title in pattern.findall(page):
        clean_title = html.unescape(re.sub(r"<.*?>", "", title)).strip()
        clean_url = html.unescape(href)
        parsed = urllib.parse.urlparse(clean_url)
        params = urllib.parse.parse_qs(parsed.query)
        if "uddg" in params:
            clean_url = params["uddg"][0]
        if clean_title and clean_url:
            results.append((clean_title, clean_url))
        if len(results) >= limit:
            break

    return results


async def web_search(query, limit=SEARCH_RESULT_LIMIT):
    if not query:
        return []

    try:
        return await asyncio.to_thread(_duckduckgo_search_sync, query, limit)
    except Exception as e:
        logger.error(f"Search Error: {e}")
        google_url = "https://www.google.com/search?" + urllib.parse.urlencode({"q": query})
        return [("Open Google results", google_url)]


async def format_search_results(query):
    results = await web_search(query)
    if not results:
        return "❌ Search result nahi mila."

    lines = [f"🔎 **Search results for:** `{query}`"]
    for idx, (title, url) in enumerate(results, start=1):
        lines.append(f"{idx}. **{title[:80]}**\n{url}")
    return "\n\n".join(lines)


def is_http_url(value):
    return bool(re.match(r"https?://", (value or "").strip(), re.I))


def extract_domain(value):
    try:
        return urllib.parse.urlparse(value).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def is_supported_music_url(value):
    domain = extract_domain(value)
    haystack = (value or "").lower()
    return any(host in domain or host in haystack for host in SUPPORTED_MUSIC_PLATFORMS)


def is_metadata_only_music_url(value):
    domain = extract_domain(value)
    haystack = (value or "").lower()
    return any(host in domain or host in haystack for host in METADATA_ONLY_MUSIC_DOMAINS)


def build_music_search_text(entry, fallback):
    parts = []
    for key in ("title", "track", "alt_title"):
        if entry.get(key):
            parts.append(str(entry[key]))
            break

    artists = entry.get("artists") or entry.get("artist") or entry.get("uploader") or entry.get("creator")
    if isinstance(artists, list):
        artists = " ".join(str(a) for a in artists[:3])
    if artists:
        parts.append(str(artists))

    text = " ".join(parts).strip()
    return text or fallback


def parse_time_to_seconds(value):
    value = (value or "").strip().lower()
    if not value:
        return None

    if ":" in value:
        total = 0
        try:
            for part in value.split(":"):
                total = total * 60 + int(part)
            return total
        except ValueError:
            return None

    match = re.search(r"(\d+)", value)
    return int(match.group(1)) if match else None


async def pause_music(chat_id):
    with suppress(Exception):
        await call_py.pause_stream(chat_id)
    AUTO_PAUSED[chat_id] = False


async def resume_music(chat_id):
    with suppress(Exception):
        await call_py.resume_stream(chat_id)
    AUTO_PAUSED[chat_id] = False


async def set_music_volume(chat_id, volume):
    VOLUME[chat_id] = max(0, min(200, int(volume)))
    with suppress(Exception):
        await call_py.change_volume_call(chat_id, VOLUME[chat_id])
    return VOLUME[chat_id]


async def seek_music(chat_id, seconds):
    if not QUEUE[chat_id]:
        return False

    seconds = max(0, int(seconds))
    await play_next(chat_id, seek=seconds)
    return True


def get_elapsed_seconds(chat_id):
    if chat_id not in PLAY_START_TIME:
        return 0
    return max(0, int(time.time() - PLAY_START_TIME[chat_id]))


def format_now_playing(chat_id):
    if not QUEUE[chat_id]:
        return "📭 Abhi kuch play nahi ho raha."

    song = QUEUE[chat_id][0]
    elapsed = get_elapsed_seconds(chat_id)
    mins, secs = divmod(elapsed, 60)
    return f"🎧 **Now Playing:** {song['title']}\n⏱ {mins}:{secs:02d} elapsed\n🔊 Volume: {VOLUME[chat_id]}%"


def format_queue(chat_id):
    if not QUEUE[chat_id]:
        return "📭 Queue khali hai."

    lines = ["🎶 **Current Queue:**"]
    for i, song in enumerate(QUEUE[chat_id][:10], start=1):
        prefix = "▶️" if i == 1 else f"{i}."
        lines.append(f"{prefix} {song['title']}")
    if len(QUEUE[chat_id]) > 10:
        lines.append(f"…and {len(QUEUE[chat_id]) - 10} more")
    return "\n".join(lines)


async def youtube_search_track(search_text):
    ydl_opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "noplaylist": True,
        "ignoreerrors": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(
                ydl.extract_info,
                f"ytsearch1:{search_text}",
                download=False
            )
        entries = info.get("entries") or [info]
        entry = next((item for item in entries if item), None)
        if not entry:
            return {"title": search_text, "url": None, "source": "YouTube Search"}
        return {
            "title": entry.get("title", search_text),
            "url": entry.get("url"),
            "source": "YouTube Search",
        }
    except Exception as e:
        logger.error(f"YouTube fallback search failed: {e}")
        return {"title": search_text, "url": None, "source": "YouTube Search"}


async def normalize_music_entry(entry, original_query):
    if not entry:
        return None

    title = entry.get("title") or entry.get("fulltitle") or "Unknown Song"
    webpage_url = entry.get("webpage_url") or entry.get("original_url") or ""
    raw_url = entry.get("url")
    search_text = build_music_search_text(entry, original_query)

    if is_metadata_only_music_url(webpage_url or original_query) or not raw_url:
        resolved = await youtube_search_track(search_text)
        if resolved.get("url"):
            resolved["title"] = resolved.get("title") or title
            return resolved

    if not raw_url:
        return None

    return {
        "title": title,
        "url": raw_url,
        "source": extract_domain(webpage_url or original_query) or "direct",
    }


async def shuffle_queue(chat_id):
    if len(QUEUE[chat_id]) <= 2:
        return False

    now_playing = QUEUE[chat_id][0]
    rest = QUEUE[chat_id][1:]
    random.shuffle(rest)
    QUEUE[chat_id] = [now_playing] + rest
    return True


async def stop_music(chat_id):
    QUEUE[chat_id].clear()
    await clear_queue_db(chat_id)
    with suppress(Exception):
        await call_py.leave_group_call(chat_id)
    ACTIVE_CALLS.discard(chat_id)
    AUTO_PAUSED[chat_id] = False


async def skip_music(chat_id):
    if not QUEUE[chat_id]:
        return None

    old = QUEUE[chat_id].pop(0)
    await remove_song_db(chat_id, old["title"])
    await asyncio.sleep(1)
    asyncio.create_task(play_next(chat_id))
    return old


async def speak_in_vc(chat_id, text, resume_music=True):
    if chat_id not in ACTIVE_CALLS or not text:
        return

    async with TTS_LOCK[chat_id]:
        TTS_PLAYING[chat_id] = True
        tts_file = f"tts_{uuid.uuid4().hex}.mp3"
        seek_pos = (
            int(time.time() - PLAY_START_TIME[chat_id]) + 2
            if chat_id in PLAY_START_TIME
            else 0
        )

        try:
            await edge_tts.Communicate(text[:450], get_chat_voice(chat_id)).save(tts_file)
            await call_py.change_stream(chat_id, AudioPiped(tts_file))
            await asyncio.sleep(max(3, len(text.split()) // 3))

            if resume_music and QUEUE.get(chat_id):
                await play_next(chat_id, seek=seek_pos)
            else:
                with suppress(Exception):
                    await call_py.change_stream(
                        chat_id,
                        AudioPiped(EMPTY_AUDIO)
                    )
        except Exception as e:
            logger.error(f"VC Speak Error: {e}")
        finally:
            TTS_PLAYING[chat_id] = False
            with suppress(Exception):
                os.remove(tts_file)



def validate_runtime_config():
    missing = []
    for name, value in (
        ("API_ID", API_ID),
        ("API_HASH", API_HASH),
        ("BOT_TOKEN", BOT_TOKEN),
        ("SESSION_STRING", SESSION_STRING),
    ):
        if not value:
            missing.append(name)

    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )


def set_language(chat_id, language):
    key = (language or "").strip().lower()
    if key not in LANGUAGE_VOICES:
        return False
    CHAT_VOICE[chat_id] = LANGUAGE_VOICES[key]
    return True


async def handle_intent(chat_id, clean_query, status=None, user_id=0, source="text"):
    clean_query = (clean_query or "").strip()
    clean = clean_query.lower()

    if not clean:
        await safe_status(status, "Ji, command boliye 🙂")
        return "Ji, command boliye."

    play_prefixes = (
        "play ", "p ", "baja ", "bajao ", "lagao ", "chalao ",
        "song ", "music ", "gaana ", "gana ", "track "
    )
    trailing_play = re.search(r"\b(play|baja|bajao|lagao|chalao)\b", clean)
    if clean.startswith(play_prefixes) or (trailing_play and (is_http_url(clean) or is_supported_music_url(clean))):
        song_name = re.sub(
            r"^(play|p|baja|bajao|lagao|chalao|song|music|gaana|gana|track)\s+",
            "",
            clean_query,
            count=1,
            flags=re.I
        ).strip()
        song_name = re.sub(r"\b(play|baja|bajao|lagao|chalao|karo|please)\b", "", song_name, flags=re.I).strip()
        if song_name:
            await handle_play(chat_id, song_name, status)
            return f"Playing {song_name}"

    if any(word in clean for word in ("pause", "ruk", "ruko", "hold", "thamo")):
        await pause_music(chat_id)
        await safe_status(status, "⏸ Paused.")
        return "Paused."

    if any(word in clean for word in ("resume", "continue", "chaloo", "chalu", "dobara", "unpause")):
        await resume_music(chat_id)
        await safe_status(status, "▶️ Resumed.")
        return "Resumed."

    if any(word in clean for word in ("skip", "next", "agla")):
        old = await skip_music(chat_id)
        msg = f"⏭ Skipped: {old['title']}" if old else "📭 Queue khali hai."
        await safe_status(status, msg)
        return msg

    if any(word in clean for word in ("stop", "band", "chup", "clear queue", "queue clear")):
        await stop_music(chat_id)
        await safe_status(status, "⏹ Stopped.")
        return "Stopped."

    if any(word in clean for word in ("leave vc", "leave call", "vc se nikal")):
        with suppress(Exception):
            await call_py.leave_group_call(chat_id)
        ACTIVE_CALLS.discard(chat_id)
        await safe_status(status, "👋 VC leave kar diya.")
        return "Left VC."

    if clean.startswith(("volume ", "vol ", "awaaz ", "sound ")):
        level = parse_time_to_seconds(clean)
        if level is None:
            msg = "Usage: volume 0-200"
        else:
            vol = await set_music_volume(chat_id, level)
            msg = f"🔊 Volume set to: {vol}%"
        await safe_status(status, msg)
        return msg

    if clean.startswith(("seek ", "jump ")):
        seconds = parse_time_to_seconds(clean.split(maxsplit=1)[1] if " " in clean else "")
        ok = await seek_music(chat_id, seconds or 0)
        msg = f"⏩ Seeked to {seconds or 0}s." if ok else "📭 Queue khali hai."
        await safe_status(status, msg)
        return msg

    if clean.startswith(("forward ", "aage ")):
        seconds = parse_time_to_seconds(clean) or 10
        target = get_elapsed_seconds(chat_id) + seconds
        ok = await seek_music(chat_id, target)
        msg = f"⏩ Forward {seconds}s." if ok else "📭 Queue khali hai."
        await safe_status(status, msg)
        return msg

    if clean.startswith(("rewind ", "peeche ", "back ")):
        seconds = parse_time_to_seconds(clean) or 10
        target = max(0, get_elapsed_seconds(chat_id) - seconds)
        ok = await seek_music(chat_id, target)
        msg = f"⏪ Rewind {seconds}s." if ok else "📭 Queue khali hai."
        await safe_status(status, msg)
        return msg

    if clean in {"queue", "list", "playlist", "songs"} or "queue dikhao" in clean:
        msg = format_queue(chat_id)
        await safe_status(status, msg)
        return msg

    if clean in {"now", "current", "now playing", "kya chal raha hai"}:
        msg = format_now_playing(chat_id)
        await safe_status(status, msg)
        return msg

    if "shuffle" in clean:
        ok = await shuffle_queue(chat_id)
        msg = "🔀 Queue shuffled." if ok else "🔀 Shuffle ke liye queue mein aur songs chahiye."
        await safe_status(status, msg)
        return msg

    if clean.startswith(("search ", "google ", "find ", "dhundo ")):
        query = re.sub(r"^(search|google|find|dhundo)\s+", "", clean_query, count=1, flags=re.I).strip()
        result_text = await format_search_results(query)
        await safe_status(status, result_text)
        return result_text[:300]

    if clean.startswith(("language ", "lang ", "speak ")):
        lang = clean.split(maxsplit=1)[1] if " " in clean else ""
        ok = set_language(chat_id, lang)
        msg = f"🌐 Voice language set: {lang}" if ok else f"❌ Supported: {', '.join(LANGUAGE_VOICES)}"
        await safe_status(status, msg)
        return msg

    memory = "\n".join(CHAT_MEMORY[chat_id])
    ans = await generate_ai_text(
        "You are Ruhi/Roohi, a fast Alexa-like Telegram VC assistant. "
        "Reply shortly in the user's language or Hinglish. If user asks about music control, "
        "tell exact commands such as play, pause, resume, skip, stop, queue, volume, seek. "
        f"Recent memory:\n{memory}\nUser: {clean_query}",
        fallback="Ji, main Ruhi hoon. Boliye?"
    )
    ans = ans[:450]
    await safe_status(status, f"🧠 {ans}")

    CHAT_MEMORY[chat_id].append(f"U:{clean_query[:120]} | R:{ans[:200]}")
    asyncio.create_task(save_chat_memory(chat_id))

    if source in {"vc", "voice_message"}:
        await speak_in_vc(chat_id, ans)

    return ans


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
                        AudioPiped(EMPTY_AUDIO)
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

    query = (query or "").strip()
    if not query:
        return

    if len(QUEUE[chat_id]) >= MAX_QUEUE_LIMIT:

        if msg:
            await safe_status(msg, "❌ Queue Full!")

        return

    is_playlist = (
        "list=" in query.lower()
        or "playlist" in query.lower()
        or "/sets/" in query.lower()
        or "/playlist/" in query.lower()
        or "/album/" in query.lower()
    )

    search = (
        f"ytsearch10:{query}"
        if is_playlist and not is_http_url(query)
        else f"ytsearch1:{query}"
    )

    ydl_opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "noplaylist": not is_playlist,
        "ignoreerrors": True,
        "default_search": "ytsearch",
    }

    try:

        with YoutubeDL(ydl_opts) as ydl:

            info = await asyncio.to_thread(
                ydl.extract_info,
                query if is_http_url(query) else search,
                download=False
            )

        if not info:
            if msg:
                await safe_status(msg, "❌ Music source se result nahi mila.")
            return

        entries = info.get("entries") or [info]

        added = 0
        added_titles = []

        for entry in entries[:MAX_PLAYLIST_SIZE]:

            data = await normalize_music_entry(entry, query)

            if not data or not data.get("url"):
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
            added_titles.append(data["title"])

        if added == 0:
            if msg:
                await safe_status(
                    msg,
                    "❌ Music nahi mila. YouTube/Spotify/SoundCloud/Apple/JioSaavn link ya song name bhejo."
                )
            return

        # Join VC
        if chat_id not in ACTIVE_CALLS:

            try:

                await call_py.join_group_call(
                    chat_id,
                    AudioPiped(EMPTY_AUDIO)
                )

                ACTIVE_CALLS.add(chat_id)

            except Exception as e:

                logger.error(
                    f"VC Join Error: {e}"
                )

                if msg:
                    await safe_status(msg, "❌ VC Join Failed. Group video chat start hai aur assistant admin hai?")

                return

        # Start Playback
        if len(QUEUE[chat_id]) <= added or seek > 0:

            await asyncio.sleep(2)

            asyncio.create_task(
                play_next(chat_id, seek=seek)
            )

        if msg:

            preview = "\n".join(f"• {title[:70]}" for title in added_titles[:3])
            extra = f"\n{preview}" if preview else ""
            await safe_status(msg, f"🎵 Added {added} track(s).{extra}")

    except Exception as e:

        logger.error(f"Play Fail: {e}")

        if msg:
            await safe_status(msg, "❌ Load Failed. Link/platform unavailable ho sakta hai.")


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
                    chat_id in ACTIVE_CALLS
                    and QUEUE.get(chat_id)
                    and not TTS_PLAYING[chat_id]
                    and not AUTO_PAUSED[chat_id]
                ):
                    with suppress(Exception):
                        await call_py.pause_stream(chat_id)
                    AUTO_PAUSED[chat_id] = True

                if (
                    len(AUDIO_BUFFER[chat_id])
                    > MAX_BUFFER_FRAMES
                ):

                    AUDIO_BUFFER[chat_id].pop(0)

            else:

                SILENCE_COUNT[chat_id] += 1

                if (
                    SILENCE_COUNT[chat_id] > 18
                    and AUTO_PAUSED[chat_id]
                    and not IS_PROCESSING[chat_id]
                    and not TTS_PLAYING[chat_id]
                ):
                    with suppress(Exception):
                        await call_py.resume_stream(chat_id)
                    AUTO_PAUSED[chat_id] = False

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
# =========================================
# 6.5 RAW VOICE PROCESSOR (AI VC TALK)
# =========================================

async def process_voice(chat_id, audio_data, user_id):
    if IS_PROCESSING[chat_id]:
        return

    IS_PROCESSING[chat_id] = True
    raw_file = f"raw_{uuid.uuid4().hex}.raw"
    wav_file = f"v_{uuid.uuid4().hex}.wav"

    try:
        with open(raw_file, "wb") as f:
            f.write(audio_data)

        await asyncio.to_thread(
            subprocess.run,
            [
                "ffmpeg", "-f", "s16le", "-ar", "48000", "-ac", "1",
                "-i", raw_file, wav_file, "-y", "-loglevel", "quiet"
            ],
            check=True
        )

        segments, _ = await asyncio.to_thread(whisper_model.transcribe, wav_file)
        text = "".join([s.text for s in segments]).strip().lower()

        if not text or len(text) < 2:
            return

        if not any(w in text for w in WAKE_WORDS):
            if AUTO_PAUSED[chat_id] and QUEUE.get(chat_id):
                with suppress(Exception):
                    await call_py.resume_stream(chat_id)
                AUTO_PAUSED[chat_id] = False
            return

        logger.info(f"VC Speech: {text}")

        clean_query = text
        for w in WAKE_WORDS:
            clean_query = clean_query.replace(w, "").strip()

        AUTO_PAUSED[chat_id] = False
        await handle_intent(chat_id, clean_query, user_id=user_id, source="vc")

    except Exception as e:
        logger.error(f"process_voice error: {e}")
    finally:
        IS_PROCESSING[chat_id] = False
        for f in [raw_file, wav_file]:
            with suppress(Exception):
                if os.path.exists(f):
                    os.remove(f)

# =========================================
# Yahan se Section 7 (VOICE MESSAGE AI) shuru hoga...
# =========================================

@bot.on_message(filters.voice)
async def voice_message_ai(_, m: Message):

    if not m.voice or not m.from_user:
        return

    chat_id = m.chat.id
    user_id = m.from_user.id
    voice_file = None

    try:
        status = await m.reply("🎤 Listening...")
        voice_file = await m.download(file_name=f"v_{uuid.uuid4().hex}.ogg")

        segs, _ = await asyncio.to_thread(whisper_model.transcribe, voice_file)
        text = "".join([s.text for s in segs]).strip().lower()

        if not text:
            return await safe_status(status, "❌ Kuch samajh nahi aya.")

        clean = text.strip()
        if not any(w in clean for w in WAKE_WORDS):
            return await safe_status(status, "👂 Wake word bolo: Ruhi ya Roohi")

        for w in WAKE_WORDS:
            clean = clean.replace(w, "").strip()

        now = time.time()
        if now - AI_COOLDOWN[user_id] < 3:
            return await safe_status(status, "⏳ Wait...")

        AI_COOLDOWN[user_id] = now
        await handle_intent(chat_id, clean, status=status, user_id=user_id, source="voice_message")

    except Exception as e:
        logger.error(f"Voice Message Handler Error: {e}")
        await m.reply("❌ Voice processing failed.")
    finally:
        if voice_file:
            with suppress(Exception):
                os.remove(voice_file)

# =========================================
# 7.5 TEXT COMMAND DISPATCHER (FIXED & SYNCED)
# =========================================

@bot.on_message(filters.command([
    "start", "help", "play", "p", "volume", "vol", "quiz", "truth", "dare",
    "skip", "next", "stop", "clear", "join", "leave", "queue", "q", "np",
    "current", "ttt", "pause", "resume", "seek", "forward", "rewind",
    "shuffle", "search", "google", "ask", "lang", "language", "ping"
], prefixes=["/", "!", "."]) & filters.incoming)
async def dispatcher(_, m: Message):
    if not m.from_user:
        return

    chat_id = m.chat.id
    cmd = m.command[0].lower()
    user_id = m.from_user.id

    admin_cmds = ["play", "p", "skip", "next", "stop", "clear", "join", "leave", "volume", "vol", "pause", "resume", "seek", "forward", "rewind", "shuffle"]
    if cmd in admin_cmds and m.chat.type != ChatType.PRIVATE:
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                return await m.reply("❌ Sirf Admins ye command chala sakte hain.")
        except Exception as e:
            logger.error(f"Admin Check Error: {e}")

    if cmd == "start":
        await m.reply(
            "✨ **Ruhi / Roohi Online**\n"
            "Main voice-command Telegram assistant hoon: VC music, AI chat, search, quiz, games, DM/group commands.\n\n"
            "Wake word: **Ruhi** ya **Roohi**. Commands ke liye /help."
        )

    elif cmd == "help":
        await m.reply(
            "📚 **Ruhi Commands:**\n\n"
            "🎵 **Music/VC:** /join, /play or /p <song/link>, /pause, /resume, /skip, /stop, /leave\n"
            "🎛 **Control:** /queue, /np, /volume 0-200, /seek 90, /forward 10, /rewind 10, /shuffle\n"
            "🌍 **Platforms:** YouTube, YouTube Music, Spotify, SoundCloud, Apple Music, Deezer, JioSaavn, Bandcamp\n"
            "🔎 **Search:** /search <query> ya /google <query>\n"
            "🧠 **AI:** /ask <question> + voice note mein 'Ruhi ...'\n"
            "🌐 **Language:** /lang hi|en|ur|es|fr|ar|hinglish\n"
            "🎮 **Games:** /ttt, /quiz, /truth, /dare\n\n"
            "🎙 **VC Voice:** 'Ruhi play despacito', 'Ruhi pause', 'Ruhi volume 80', 'Ruhi forward 30', 'Ruhi search latest news'."
        )

    elif cmd == "ping":
        await m.reply("🏓 Pong! Ruhi ready hai.")

    elif cmd in {"play", "p"}:
        query = " ".join(m.command[1:]).strip()
        if not query:
            return await m.reply("🎵 Gaane ka naam ya link toh do bhai.")

        now = time.time()
        if now - PLAY_COOLDOWN[chat_id] < 3:
            return await m.reply("⏳ Sabar karo, 3 second ruko.")

        PLAY_COOLDOWN[chat_id] = now
        status = await m.reply("🔍 Searching...")
        await handle_play(chat_id, query, status)

    elif cmd in {"stop", "clear"}:
        await stop_music(chat_id)
        await m.reply("⏹ Music band aur Queue saaf kar di hai.")

    elif cmd in {"skip", "next"}:
        old = await skip_music(chat_id)
        if not old:
            return await m.reply("📭 Queue mein kuch hai hi nahi skip karne ko.")
        await m.reply(f"⏭ Skipped: **{old['title']}**")

    elif cmd in {"queue", "q"}:
        await m.reply(format_queue(chat_id))

    elif cmd in {"np", "current"}:
        await m.reply(format_now_playing(chat_id))

    elif cmd == "join":
        if m.chat.type == ChatType.PRIVATE:
            return await m.reply("❌ VC join group mein hota hai. Mujhe group mein add karke /join use karo.")
        if chat_id in ACTIVE_CALLS:
            return await m.reply("🎙 Main pehle se VC mein hu.")
        try:
            await call_py.join_group_call(chat_id, AudioPiped(EMPTY_AUDIO))
            ACTIVE_CALLS.add(chat_id)
            await m.reply("🎙 VC Join kar liya hai!")
        except NoActiveGroupCall:
            await m.reply("❌ Pehle Group mein Video Chat start karo.")
        except Exception as e:
            logger.error(f"Join Fail: {e}")
            await m.reply("❌ VC join failed.")

    elif cmd == "leave":
        with suppress(Exception):
            await call_py.leave_group_call(chat_id)
        ACTIVE_CALLS.discard(chat_id)
        await m.reply("👋 VC leave kar diya.")

    elif cmd in {"volume", "vol"}:
        if len(m.command) < 2:
            return await m.reply("Usage: /volume 0-200")
        try:
            vol = await set_music_volume(chat_id, int(m.command[1]))
            await m.reply(f"🔊 Volume set to: {vol}%")
        except Exception:
            await m.reply("❌ Sahi number daalo (0-200).")

    elif cmd == "pause":
        await pause_music(chat_id)
        await m.reply("⏸ Paused.")

    elif cmd == "resume":
        await resume_music(chat_id)
        await m.reply("▶️ Resumed.")

    elif cmd in {"seek", "forward", "rewind"}:
        seconds = parse_time_to_seconds(" ".join(m.command[1:]))
        if seconds is None:
            return await m.reply("Usage: /seek 90, /forward 10, /rewind 10")
        if cmd == "forward":
            seconds = get_elapsed_seconds(chat_id) + seconds
        elif cmd == "rewind":
            seconds = max(0, get_elapsed_seconds(chat_id) - seconds)
        ok = await seek_music(chat_id, seconds)
        await m.reply(f"⏩ Seek set to {seconds}s." if ok else "📭 Queue khali hai.")

    elif cmd == "shuffle":
        ok = await shuffle_queue(chat_id)
        await m.reply("🔀 Queue shuffled." if ok else "🔀 Shuffle ke liye queue mein aur songs chahiye.")

    elif cmd in {"search", "google"}:
        query = " ".join(m.command[1:]).strip()
        if not query:
            return await m.reply("🔎 Search query likho.")
        status = await m.reply("🔎 Searching web...")
        await safe_status(status, await format_search_results(query))

    elif cmd == "ask":
        query = " ".join(m.command[1:]).strip()
        if not query:
            return await m.reply("🧠 Sawal likho: /ask ...")
        status = await m.reply("🧠 Thinking...")
        await handle_intent(chat_id, query, status=status, user_id=user_id, source="text")

    elif cmd in {"lang", "language"}:
        language = " ".join(m.command[1:]).strip()
        if not language:
            return await m.reply(f"🌐 Supported: {', '.join(LANGUAGE_VOICES)}")
        if set_language(chat_id, language):
            await m.reply(f"🌐 Ruhi voice language set: **{language}**")
        else:
            await m.reply(f"❌ Supported: {', '.join(LANGUAGE_VOICES)}")

    elif cmd == "quiz":
        try:
            prompt = "Generate 1 difficult NEET MCQ. Format exactly: Question|OptA|OptB|OptC|OptD|CorrectLetter"
            text = await generate_ai_text(prompt, fallback="")
            res = text.split("|")
            if len(res) >= 6:
                QUIZ_DATA[chat_id] = res[5].strip().upper()[:1]
                buttons = [[InlineKeyboardButton(res[i+1].strip(), callback_data=f"qz_{chr(65+i)}")] for i in range(4)]
                await m.reply(f"📖 **Quiz:** {res[0]}", reply_markup=InlineKeyboardMarkup(buttons))
            else:
                await m.reply("❌ Quiz format nahi bana, firse try karo.")
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

    validate_runtime_config()

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