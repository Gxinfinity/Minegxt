# Ruhi / Roohi Telegram Voice Assistant

Ruhi is a Telegram bot + assistant account setup for group video chat music, voice commands, AI replies, web search, quiz, and games. It is designed to feel like a premium natural Ruhi/Roohi assistant in Telegram groups: say `Ruhi play ...`, `Ruhi pause`, `Ruhi volume 80`, or `Ruhi search ...` while the bot is in VC.

## Main features

- Wake words: `Ruhi` and `Roohi`
- Pyrogram v2-style commands with `/`, `!`, and `.` prefixes
- Group VC music: `/join`, `/play` or `/p`, `/pause`, `/resume`, `/skip`, `/stop`, `/leave`, `/queue`, `/np`
- Music controls: `/volume 0-200`, `/seek 90`, `/forward 10`, `/rewind 10`, `/shuffle`, `/clear`
- Multi-platform music input through `yt-dlp`: YouTube, YouTube Music, Spotify, SoundCloud, Apple Music, Deezer, JioSaavn/Saavn, Bandcamp, plus normal song names
- Voice commands from Telegram voice notes and supported raw VC audio callbacks
- Auto-pauses music while users speak in VC, then resumes after silence
- Web results in groups/DMs: `/search <query>` or voice command `Ruhi search <query>`
- AI chat in DM/group: `/ask <question>` or voice command `Ruhi <question>`
- Multi-language TTS voice selection: `/lang hi|en|ur|es|fr|ar|hinglish`
- Games: `/ttt`, `/quiz`, `/truth`, `/dare`

## Required environment variables

Never hard-code production credentials in `bot.py`. Copy `.env.example` locally and fill in real values. `python-dotenv` is included in `requirements.txt`, so local `.env` files load automatically when you run `python bot.py`:

```bash
cp .env.example .env
```

Required:

```bash
API_ID=123456
API_HASH=telegram-api-hash
BOT_TOKEN=123:bot-token
SESSION_STRING=pyrogram-assistant-session
```

Optional:

```bash
GEMINI_API_KEY=gemini-key
LOGGER_ID=-1003009782265
RUHI_DEFAULT_VOICE=hi-IN-SwaraNeural
```

## Local/VPS run

Install system packages and Python dependencies, then run the worker:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv ffmpeg
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt
python bot.py
```

### VPS systemd deployment

A helper script and systemd template are included:

```bash
sudo mkdir -p /opt/mineruhi
sudo cp -r . /opt/mineruhi
sudo chown -R "$USER":"$USER" /opt/mineruhi
cd /opt/mineruhi
./deploy/vps_setup.sh
nano .env
sudo cp deploy/ruhi.service.example /etc/systemd/system/ruhi.service
sudo systemctl daemon-reload
sudo systemctl enable --now ruhi
sudo journalctl -u ruhi -f
```

## Heroku deployment

This repo includes Heroku-ready files:

- `Procfile` runs the bot as a worker dyno.
- `requirements.txt` installs all Python runtime dependencies, including `python-dotenv` for VPS/local `.env` loading.
- `runtime.txt` pins Python.
- `Aptfile` installs `ffmpeg` through the Heroku Apt buildpack.
- `app.json` documents required config vars and buildpacks.

Manual Heroku deploy:

```bash
heroku create your-ruhi-bot
heroku buildpacks:add --index 1 heroku-community/apt
heroku buildpacks:add --index 2 heroku/python
heroku config:set API_ID="123456"
heroku config:set API_HASH="telegram-api-hash"
heroku config:set BOT_TOKEN="123:bot-token"
heroku config:set SESSION_STRING="pyrogram-assistant-session"
heroku config:set GEMINI_API_KEY="gemini-key"
git push heroku HEAD:main
heroku ps:scale worker=1
heroku logs --tail
```

## Text command examples

- `/join`
- `/p apna bana le`
- `/play https://open.spotify.com/track/...`
- `/play https://soundcloud.com/...`
- `/pause`, `/resume`, `/skip`, `/stop`
- `/seek 1:30`, `/forward 30`, `/rewind 10`
- `/volume 80`, `/queue`, `/np`, `/shuffle`

## Voice examples

- `Ruhi play apna bana le`
- `Roohi Spotify link play karo`
- `Ruhi pause`
- `Ruhi resume`
- `Ruhi volume 80`
- `Ruhi forward 30`
- `Ruhi search best AI news today`
- `Ruhi language english`

## Production architecture

RUHI SUPREME AI is now split into focused async services:

- `core/` — config, logging, application bootstrap, typed models
- `database/` — SQLite queue and memory persistence
- `music/` — yt-dlp resolving, queue, VC playback, seek, pause/resume, recovery state
- `voice/` — faster-whisper transcription, VAD helpers, Edge TTS VC speech interruption
- `ai/` — wake-word intent routing and Ruhi/Roohi personality control
- `services/` — Gemini AI, weather, search, TTS
- `modules/` — Pyrogram text/voice handlers and group UX
- `utils/` — async helpers

## Root cause analysis of the previous unstable build

1. Legacy PyTgCalls imports were mixed with newer `py-tgcalls` expectations, which caused raw VC listener messages such as `Raw VC listener unsupported` on modern installs.
2. Secrets were embedded or had unsafe defaults, so Heroku/VPS configuration could silently start with invalid credentials.
3. Voice, music, AI, database, and Telegram handlers were all coupled in one large file, making locks, cleanup, and reconnect logic fragile.
4. Blocking work such as `ffmpeg`, Whisper, and `yt-dlp` was not consistently isolated from the event loop.
5. Queue state and voice/TTS interruptions did not have a single owner, which made music resume and stream switching race-prone.
6. Requirements were incomplete for production VPS/Heroku deployment.

## Voice chat implementation notes

The project targets the current `py-tgcalls` package (`2.2.12+`) which is the maintained PyTgCalls distribution and is backed by NTgCalls. PyPI documents `py-tgcalls` as an async Telegram calls client, requiring Python 3.10+ and supporting Pyrogram, while the underlying project is powered by NTgCalls. The historical raw API is documented around `GroupCallRaw` / recorded PCM callbacks; Ruhi keeps all raw PCM processing isolated in `voice/assistant.py` so newer callback/event adapters can feed `VoiceAssistant.ingest_raw_frame(...)` without touching command/music logic.

## Weather setup

Weather works when this optional key is configured:

```bash
OPENWEATHER_API_KEY=your_openweather_key
```

Without it, Ruhi replies naturally and tells you the key is missing instead of crashing.

## VPS optimization tips

- Use Python 3.11+ and Linux for `uvloop` and PyTgCalls/NTgCalls wheels.
- Install `ffmpeg` system-wide and keep `yt-dlp` updated.
- Use a systemd service with `Restart=always` and monitor logs with `journalctl -u ruhi -f`.
- Keep `faster-whisper` on `tiny`/CPU for low-memory VPS plans; upgrade to GPU or larger models only if RAM allows.
- Put temp files on SSD-backed storage and clean old `tmp/` files during deploys.
- Use one worker dyno/process per assistant session to avoid Telegram session conflicts.
