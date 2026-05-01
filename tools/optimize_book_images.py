#!/usr/bin/env python3
"""Create lightweight thumbnails for extracted book images.

Uses PyMuPDF only, already required by the project. Full extracted images stay
local; thumbnails are also ignored by Git by default.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMAGES_JSON = ROOT / "content" / "extracted" / "book_images.json"
THUMBS_DIR = ROOT / "content" / "extracted" / "book_thumbs"
MAX_THUMB_SIDE = 520


def main() -> int:
    try:
        import fitz  # type: ignore
    except ImportError:
        safe_print("Install dependencies with: pip install -r requirements.txt")
        return 1

    if not IMAGES_JSON.exists():
        safe_print("No book image metadata found. Run tools/extract_book_images.py first.")
        return 0

    images = json.loads(IMAGES_JSON.read_text(encoding="utf-8"))
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    created = 0

    for item in images:
        file_path = ROOT / str(item.get("file", ""))
        if not item.get("usable") or not file_path.exists():
            continue
        thumb_path = THUMBS_DIR / f"{item['id']}.png"
        try:
            pix = fitz.Pixmap(str(file_path))
            while max(pix.width, pix.height) > MAX_THUMB_SIDE:
                pix.shrink(1)
            pix.save(thumb_path)
        except Exception as error:
            safe_print(f"Skipping thumbnail {item.get('id')}: {error}")
            continue
        item["thumbnail"] = relative(thumb_path)
        created += 1

    IMAGES_JSON.write_text(json.dumps(images, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    safe_print(f"Thumbnails created: {created}")
    safe_print(f"Updated {relative(IMAGES_JSON)}")
    return 0


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
