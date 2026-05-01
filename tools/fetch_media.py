#!/usr/bin/env python3
"""Fetch lightweight media metadata for Trading Reels AI lessons.

Uses Pexels first and Pixabay as fallback. API keys must be provided through
environment variables. The script stores metadata and remote URLs only; it does
not download media into the repository.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSONS_FILE = ROOT / "content" / "lessons.json"
MEDIA_FILE = ROOT / "content" / "media.json"
TIMEOUT_SECONDS = 18


def main() -> int:
    lessons = load_lessons()
    pexels_key = os.environ.get("PEXELS_API_KEY")
    pixabay_key = os.environ.get("PIXABAY_API_KEY")

    if not pexels_key and not pixabay_key:
        write_json([])
        safe_print("PEXELS_API_KEY and PIXABAY_API_KEY are missing. Wrote empty content/media.json fallback.")
        return 0

    media_items = []
    for lesson in lessons:
        query = lesson.get("media_query") or lesson.get("image_query") or "trading chart dark finance"
        item = None
        if pexels_key:
            item = fetch_pexels_media(str(query), lesson["id"], pexels_key)
        if not item and pixabay_key:
            item = fetch_pixabay_image(str(query), lesson["id"], pixabay_key)
        if item:
            media_items.append(item)

    write_json(media_items)
    pexels_count = sum(1 for item in media_items if item.get("source") == "pexels")
    pixabay_count = sum(1 for item in media_items if item.get("source") == "pixabay")
    safe_print(f"Lessons read: {len(lessons)}")
    safe_print(f"Media items found: {len(media_items)}")
    safe_print(f"Pexels: {pexels_count}")
    safe_print(f"Pixabay: {pixabay_count}")
    safe_print(f"Wrote {relative(MEDIA_FILE)}")
    return 0


def load_lessons() -> list[dict[str, object]]:
    if not LESSONS_FILE.exists():
        return []
    data = json.loads(LESSONS_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("lessons", [])


def fetch_pexels_media(query: str, lesson_id: str, api_key: str) -> dict[str, object] | None:
    video = fetch_pexels_video(query, lesson_id, api_key)
    if video and is_trading_relevant(video, query):
        return video
    image = fetch_pexels_image(query, lesson_id, api_key)
    if image and is_trading_relevant(image, query):
        return image
    return image


def fetch_pexels_image(query: str, lesson_id: str, api_key: str) -> dict[str, object] | None:
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode({"query": query, "per_page": 5, "orientation": "portrait"})
    data = request_json(url, {"Authorization": api_key})
    for photo in data.get("photos", []):
        src = photo.get("src", {})
        if src.get("large2x") or src.get("large"):
            return {
                "lesson_id": lesson_id,
                "type": "image",
                "url": src.get("large2x") or src.get("large"),
                "preview_url": src.get("medium") or src.get("small"),
                "source": "pexels",
                "author": photo.get("photographer", "Pexels contributor"),
                "author_url": photo.get("photographer_url", "https://www.pexels.com"),
                "source_url": photo.get("url", "https://www.pexels.com"),
                "license": "Pexels License",
                "query": query,
            }
    return None


def fetch_pexels_video(query: str, lesson_id: str, api_key: str) -> dict[str, object] | None:
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": query, "per_page": 5, "orientation": "portrait"})
    data = request_json(url, {"Authorization": api_key})
    for video in data.get("videos", []):
        files = sorted(video.get("video_files", []), key=lambda item: item.get("width", 9999))
        chosen = next((item for item in files if item.get("file_type") == "video/mp4" and 540 <= item.get("width", 0) <= 1280), None)
        if chosen:
            user = video.get("user", {})
            return {
                "lesson_id": lesson_id,
                "type": "video",
                "url": chosen.get("link"),
                "poster": video.get("image"),
                "source": "pexels",
                "author": user.get("name", "Pexels contributor"),
                "author_url": user.get("url", "https://www.pexels.com"),
                "source_url": video.get("url", "https://www.pexels.com"),
                "license": "Pexels License",
                "query": query,
            }
    return None


def fetch_pixabay_image(query: str, lesson_id: str, api_key: str) -> dict[str, object] | None:
    url = "https://pixabay.com/api/?" + urllib.parse.urlencode({
        "key": api_key,
        "q": query,
        "image_type": "photo",
        "orientation": "vertical",
        "safesearch": "true",
        "per_page": 5,
    })
    data = request_json(url, {})
    for hit in data.get("hits", []):
        if hit.get("largeImageURL") or hit.get("webformatURL"):
            return {
                "lesson_id": lesson_id,
                "type": "image",
                "url": hit.get("largeImageURL") or hit.get("webformatURL"),
                "preview_url": hit.get("webformatURL") or hit.get("previewURL"),
                "source": "pixabay",
                "author": hit.get("user", "Pixabay contributor"),
                "author_url": f"https://pixabay.com/users/{hit.get('user', '')}-{hit.get('user_id', '')}/",
                "source_url": hit.get("pageURL", "https://pixabay.com"),
                "license": "Pixabay Content License",
                "query": query,
            }
    return None


def request_json(url: str, headers: dict[str, str]) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": "TradingReelsAI/1.0", **headers})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        safe_print(f"Media request failed: {error}")
        return {}


def is_trading_relevant(item: dict[str, object], query: str) -> bool:
    haystack = " ".join(str(item.get(key, "")) for key in ["url", "preview_url", "poster", "source_url", "query"]).lower()
    terms = ["trading", "chart", "market", "finance", "stock", "candlestick", "dashboard", "screen"]
    return any(term in haystack or term in query.lower() for term in terms)


def write_json(data: list[dict[str, object]]) -> None:
    MEDIA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def safe_print(message: object) -> None:
    text = str(message)
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, errors="backslashreplace").decode(encoding))


if __name__ == "__main__":
    sys.exit(main())
