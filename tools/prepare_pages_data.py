#!/usr/bin/env python3
"""Prepare safe runtime data for Cloudflare Pages frontend deployment."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
FRONTEND_DATA = ROOT / "frontend" / "data"
BOOK_IMAGE_DIR = FRONTEND_DATA / "book_images"


DEFAULT_CREDITS = {
    "policy": "Trading Reels AI uses educational local content and safe generated visuals. Optional media credits are listed when metadata is available.",
    "sources": [
        {
            "name": "Generated CSS market visuals",
            "type": "local-interface-visual",
            "note": "Used as the safe default fallback when media or book images are unavailable.",
        }
    ],
}


def main() -> int:
    FRONTEND_DATA.mkdir(parents=True, exist_ok=True)
    BOOK_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    lessons = read_json(CONTENT / "lessons.json", [])
    copied = copy_referenced_book_images(lessons)
    write_json(FRONTEND_DATA / "lessons.json", lessons)

    media = read_json(CONTENT / "media.json", [])
    write_json(FRONTEND_DATA / "media.json", media if isinstance(media, list) else [])

    credits = read_json(CONTENT / "credits.json", DEFAULT_CREDITS)
    write_json(FRONTEND_DATA / "credits.json", credits if isinstance(credits, dict) else DEFAULT_CREDITS)

    safe_print(f"Prepared frontend/data with {len(lessons)} lessons")
    safe_print(f"Copied referenced book images: {copied}")
    return 0


def copy_referenced_book_images(lessons: list[dict]) -> int:
    copied = 0
    seen = set()
    for lesson in lessons:
        media = lesson.get("book_media")
        if not isinstance(media, dict):
            continue
        source_url = str(media.get("url") or "")
        source_path = resolve_project_path(source_url)
        if not source_path or not source_path.exists():
            continue
        target_name = source_path.name
        target_path = BOOK_IMAGE_DIR / target_name
        if target_name not in seen:
            shutil.copy2(source_path, target_path)
            seen.add(target_name)
            copied += 1
        media["url"] = f"./data/book_images/{target_name}"
        media.pop("thumbnail", None)
    return copied


def resolve_project_path(value: str) -> Path | None:
    if not value:
        return None
    clean = value.replace("\\", "/")
    while clean.startswith("../"):
        clean = clean[3:]
    if clean.startswith("./"):
        clean = clean[2:]
    return ROOT / clean


def read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def safe_print(message: object) -> None:
    text = str(message)
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, errors="backslashreplace").decode(encoding))


if __name__ == "__main__":
    sys.exit(main())
