# Ruhi / Roohi Telegram Voice Assistant

Ruhi is a Telegram bot + assistant account setup for group video chat music, voice commands, AI replies, web search, quiz, and games. It is designed to feel Alexa-like in Telegram groups: say `Ruhi play ...`, `Ruhi pause`, `Ruhi volume 80`, or `Ruhi search ...` while the bot is in VC.

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

Never hard-code production credentials in `bot.py`. Export these before running:

```bash
export API_ID="33745438"
export API_HASH="telegram-api-hash"
export BOT_TOKEN="123:bot-token"
export SESSION_STRING="pyrogram-assistant-session"
export GEMINI_API_KEY="gemini-key"
```

Optional:

```bash
export LOGGER_ID="-1003009782265"
export RUHI_DEFAULT_VOICE="hi-IN-SwaraNeural"
```

## Run

Install the Python dependencies used by the bot, ensure `ffmpeg` is available, start a Telegram group video chat, then run:

```bash
python bot.py
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
