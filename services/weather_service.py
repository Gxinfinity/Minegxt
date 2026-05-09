from __future__ import annotations

import aiohttp

from core.config import Settings


class WeatherService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def weather(self, query: str) -> str:
        city = self._city_from_query(query)
        if not city:
            return "City ka naam batao na, jaise: Ruhi weather Delhi 😭"
        if not self.settings.openweather_api_key:
            return f"{city} ka weather batane ke liye OPENWEATHER_API_KEY set karna hoga baby 🌦️"
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": self.settings.openweather_api_key, "units": "metric"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=12) as resp:
                if resp.status != 200:
                    return f"{city} ka weather nahi mila 😭 city spelling check karo."
                data = await resp.json()
        temp = round(data["main"]["temp"])
        feels = round(data["main"].get("feels_like", temp))
        desc = data["weather"][0]["description"]
        return f"{city} me abhi {temp}°C hai, feels like {feels}°C — {desc}. Dhyaan rakhna okay? 🥺"

    def _city_from_query(self, query: str) -> str:
        cleaned = query.lower()
        for token in ("weather", "mausam", "bata", "ka", "me", "mein", "ruhi", "roohi"):
            cleaned = cleaned.replace(token, " ")
        return " ".join(cleaned.split()).title()
