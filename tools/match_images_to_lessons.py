#!/usr/bin/env python3
"""Attach extracted book images to active lessons when suitable."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSONS_FILE = ROOT / "content" / "lessons.json"
IMAGES_FILE = ROOT / "content" / "extracted" / "book_images.json"


def main() -> int:
    lessons = load_json(LESSONS_FILE, [])
    images = [item for item in load_json(IMAGES_FILE, []) if item.get("usable") and image_exists(item)]

    if not lessons:
        safe_print("No lessons found.")
        return 0
    if not images:
        safe_print("No usable book images found. Lessons left unchanged.")
        return 0

    matched = 0
    for index, lesson in enumerate(lessons):
        image = choose_image(lesson, images, index)
        if not image:
            continue
        lesson["book_media"] = {
            "type": "image",
            "url": "../" + image["file"],
            "thumbnail": "../" + image.get("thumbnail", image["file"]),
            "source": "book-extracted",
        }
        matched += 1

    LESSONS_FILE.write_text(json.dumps(lessons, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    safe_print(f"Usable book images: {len(images)}")
    safe_print(f"Lessons matched with book images: {matched}")
    safe_print(f"Updated {relative(LESSONS_FILE)}")
    return 0


def choose_image(lesson: dict[str, object], images: list[dict[str, object]], index: int) -> dict[str, object] | None:
    topic = str(lesson.get("topic", "")).lower()
    portrait = [image for image in images if image.get("aspect_ratio", 1) < 1]
    landscape = [image for image in images if image.get("aspect_ratio", 1) >= 1]
    large = [image for image in images if "large" in image.get("tags", [])]
    candle = [image for image in images if "candlestick" in image.get("tags", [])]

    if "candle" in topic:
        pool = candle or large or images
    elif any(key in topic for key in ["liquidity", "support", "structure", "entries"]):
        pool = landscape or large or images
    elif "risk" in topic or "psychology" in topic:
        pool = portrait or large or images
    else:
        pool = large or images

    return pool[index % len(pool)] if pool else None


def image_exists(item: dict[str, object]) -> bool:
    file_path = item.get("file")
    return isinstance(file_path, str) and (ROOT / file_path).exists()


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


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
