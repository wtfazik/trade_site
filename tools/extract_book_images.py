#!/usr/bin/env python3
"""Extract chart-like images from local trading PDFs.

PDF filenames stay local-only. Metadata uses `book_source: hidden` so the
frontend never exposes source book names.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOKS_DIR = ROOT / "content" / "books"
OUTPUT_DIR = ROOT / "content" / "extracted" / "book_images"
METADATA_FILE = ROOT / "content" / "extracted" / "book_images.json"
MIN_WIDTH = 360
MIN_HEIGHT = 240
MIN_AREA = 140_000


def main() -> int:
    try:
        import fitz  # type: ignore
    except ImportError:
        safe_print("Install dependencies with: pip install -r requirements.txt")
        return 1

    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(BOOKS_DIR.glob("*.pdf"))
    metadata = []
    extracted = 0
    usable = 0
    seen = set()

    for pdf in pdfs:
        try:
            document = fitz.open(pdf)
        except Exception as error:
            safe_print(f"Skipping unreadable PDF: {safe_name(pdf)} ({error})")
            continue

        with document:
            for page_index in range(document.page_count):
                page = document[page_index]
                for image in page.get_images(full=True):
                    xref = image[0]
                    if (pdf.name, xref) in seen:
                        continue
                    seen.add((pdf.name, xref))
                    try:
                        pixmap = fitz.Pixmap(document, xref)
                        if pixmap.alpha or pixmap.n > 4:
                            pixmap = fitz.Pixmap(fitz.csRGB, pixmap)
                    except Exception:
                        continue

                    width, height = pixmap.width, pixmap.height
                    is_usable = is_usable_image(width, height)
                    tags = image_tags(width, height, is_usable)
                    if not is_usable:
                        continue

                    extracted += 1
                    usable += 1
                    image_id = f"book-img-{extracted:03d}"
                    output_path = OUTPUT_DIR / f"{image_id}.png"
                    try:
                        pixmap.save(output_path)
                    except Exception:
                        continue

                    metadata.append({
                        "id": image_id,
                        "book_source": "hidden",
                        "page": page_index + 1,
                        "file": relative(output_path),
                        "width": width,
                        "height": height,
                        "aspect_ratio": round(width / max(height, 1), 3),
                        "tags": tags,
                        "usable": is_usable,
                    })

    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    METADATA_FILE.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    safe_print(f"PDF files scanned: {len(pdfs)}")
    safe_print(f"Images extracted: {extracted}")
    safe_print(f"Usable images: {usable}")
    safe_print(f"Metadata written: {relative(METADATA_FILE)}")
    return 0


def is_usable_image(width: int, height: int) -> bool:
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        return False
    if width * height < MIN_AREA:
        return False
    aspect = width / max(height, 1)
    return 0.55 <= aspect <= 3.6


def image_tags(width: int, height: int, usable: bool) -> list[str]:
    tags = ["book-extracted"]
    aspect = width / max(height, 1)
    if usable:
        tags.extend(["chart", "trading"])
    if 0.75 <= aspect <= 2.4:
        tags.append("candlestick")
    if width >= 900 or height >= 700:
        tags.append("large")
    return tags


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def safe_name(path: Path) -> str:
    return path.name.encode(sys.stdout.encoding or "utf-8", errors="backslashreplace").decode(sys.stdout.encoding or "utf-8")


def safe_print(message: object) -> None:
    text = str(message)
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, errors="backslashreplace").decode(encoding))


if __name__ == "__main__":
    sys.exit(main())
