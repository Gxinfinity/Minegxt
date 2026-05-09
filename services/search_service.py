from __future__ import annotations

import asyncio
import html
import re
import urllib.parse
import urllib.request


class SearchService:
    async def search(self, query: str, limit: int = 5) -> str:
        results = await asyncio.to_thread(self._search_sync, query, limit)
        if not results:
            url = "https://www.google.com/search?" + urllib.parse.urlencode({"q": query})
            return f"🔎 Google result: {url}"
        lines = [f"🔎 **Results for:** `{query}`"]
        for i, (title, url) in enumerate(results, 1):
            lines.append(f"{i}. **{title[:80]}**\n{url}")
        return "\n\n".join(lines)

    def _search_sync(self, query: str, limit: int) -> list[tuple[str, str]]:
        url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 RuhiSupreme/1.0"})
        with urllib.request.urlopen(req, timeout=12) as response:
            page = response.read().decode("utf-8", errors="ignore")
        pattern = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
        results = []
        for href, title in pattern.findall(page):
            clean_title = html.unescape(re.sub(r"<.*?>", "", title)).strip()
            clean_url = html.unescape(href)
            params = urllib.parse.parse_qs(urllib.parse.urlparse(clean_url).query)
            if "uddg" in params:
                clean_url = params["uddg"][0]
            if clean_title and clean_url:
                results.append((clean_title, clean_url))
            if len(results) >= limit:
                break
        return results
