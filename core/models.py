from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Track:
    title: str
    url: str
    webpage_url: str = ""
    duration: int = 0
    source: str = "yt-dlp"
