#!/usr/bin/env python3
"""Create first-draft reel lessons from local PDF books.

This is intentionally deterministic and conservative. It extracts readable text,
splits it into short chunks, and writes draft cards for human review.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOKS_DIR = ROOT / "content" / "books"
OUTPUT_FILE = ROOT / "content" / "lessons.generated.json"
MAX_LESSONS_PER_BOOK = 40
MIN_WORDS = 28
MAX_WORDS = 75
MAX_SHORT_TEXT_CHARS = 210


def main() -> int:
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(BOOKS_DIR.glob("*.pdf"))

    if not pdfs:
        OUTPUT_FILE.write_text("[]\n", encoding="utf-8")
        safe_print(f"No PDFs found in {relative(BOOKS_DIR)}.")
        safe_print("Add your licensed books locally as PDF files, then run:")
        safe_print("  python tools/pdf_to_lessons.py")
        safe_print(f"Created empty output: {relative(OUTPUT_FILE)}")
        return 0

    try:
        import fitz  # type: ignore
    except ImportError:
        print("Install dependencies with: pip install -r requirements.txt")
        return 1

    lessons = []
    seen_chunks = set()
    for pdf in pdfs:
        safe_print(f"Reading {relative(pdf)}")
        try:
            pages = extract_pdf_pages(fitz, pdf)
        except Exception as error:
            safe_print(f"Skipping {relative(pdf)}: {error}")
            continue
        text = clean_text(remove_repeated_lines(pages))
        chunks = split_into_chunks(text, seen_chunks)
        for chunk in chunks[:MAX_LESSONS_PER_BOOK]:
            lesson = build_lesson(len(lessons) + 1, chunk, pdf)
            if lesson:
                lessons.append(lesson)

    OUTPUT_FILE.write_text(json.dumps(lessons, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    safe_print(f"Generated {len(lessons)} draft lessons at {relative(OUTPUT_FILE)}")
    safe_print("Review generated lessons before copying them into content/lessons.json.")
    safe_print("Never commit the source PDF files in content/books/.")
    return 0


def extract_pdf_pages(fitz, pdf_path: Path) -> list[str]:
    pages = []
    with fitz.open(pdf_path) as document:
        for page in document:
            pages.append(page.get_text("text"))
    return pages


def remove_repeated_lines(pages: list[str]) -> str:
    line_counts: Counter[str] = Counter()
    page_lines = []

    for page in pages:
        lines = [normalize_line(line) for line in page.splitlines()]
        lines = [line for line in lines if line]
        page_lines.append(lines)
        line_counts.update(set(lines))

    repeated = {
        line
        for line, count in line_counts.items()
        if count >= 3 and (count / max(len(pages), 1) >= 0.35 or looks_like_page_marker(line))
    }

    cleaned_pages = []
    for lines in page_lines:
        kept = [line for line in lines if line not in repeated and not looks_like_page_marker(line)]
        cleaned_pages.append(" ".join(kept))

    return "\n".join(cleaned_pages)


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"([a-z])([A-Z])", r"\1. \2", text)
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
    text = re.sub(r"\s*[-–—]{2,}\s*", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s.,;:!?$%()'\"/-]", "", text)
    return text.strip()


def normalize_line(line: str) -> str:
    line = line.replace("\u00a0", " ")
    line = re.sub(r"\s+", " ", line).strip()
    return line


def looks_like_page_marker(line: str) -> bool:
    if re.fullmatch(r"\d{1,4}", line):
        return True
    if re.fullmatch(r"page\s+\d+(\s+of\s+\d+)?", line, re.I):
        return True
    return False


def split_into_chunks(text: str, seen_chunks: set[str]) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = []
    current_words = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or is_messy(sentence):
            continue

        words = sentence.split()
        if len(words) > MAX_WORDS:
            continue

        if current_words + len(words) > MAX_WORDS and current:
            maybe_add_chunk(chunks, " ".join(current), seen_chunks)
            current = []
            current_words = 0

        current.append(sentence)
        current_words += len(words)

    if current:
        maybe_add_chunk(chunks, " ".join(current), seen_chunks)

    return chunks


def maybe_add_chunk(chunks: list[str], chunk: str, seen_chunks: set[str]) -> None:
    chunk = clean_text(chunk)
    words = chunk.split()
    fingerprint = re.sub(r"\W+", "", chunk.lower())[:180]
    if fingerprint in seen_chunks:
        return
    if MIN_WORDS <= len(words) <= MAX_WORDS and not is_messy(chunk):
        seen_chunks.add(fingerprint)
        chunks.append(chunk)


def is_messy(text: str) -> bool:
    if len(text) < 80:
        return True
    letters = sum(char.isalpha() for char in text)
    if letters / max(len(text), 1) < 0.55:
        return True
    ascii_letters = sum(("a" <= char.lower() <= "z") for char in text)
    if ascii_letters / max(letters, 1) < 0.9:
        return True
    upper_words = re.findall(r"\b[A-Z]{3,}\b", text)
    if len(upper_words) > 8:
        return True
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text.lower())
    if len(words) != len(set(words)) and most_common_word_ratio(words) > 0.18:
        return True
    if re.search(r"(copyright|all rights reserved|isbn|table of contents|\bi will\b|\bi hope\b|\bshare my own experience\b|\bwelcome\b|\bthank you\b|what is an alchemist|\btranslation:)", text, re.I):
        return True
    return False


def most_common_word_ratio(words: list[str]) -> float:
    if not words:
        return 0.0
    _word, count = Counter(words).most_common(1)[0]
    return count / len(words)


def build_lesson(index: int, chunk: str, source_pdf: Path) -> dict[str, object] | None:
    short_text = trim_sentence(chunk, MAX_SHORT_TEXT_CHARS)
    if is_messy(short_text):
        return None

    title = make_title(short_text)
    topic = infer_topic(short_text)
    return {
        "id": f"generated-{index:04d}",
        "title": title,
        "topic": topic,
        "short_text": short_text,
        "simple_explanation": f"In simple terms: {short_text}",
        "example": "Review the original book context and add a concrete chart example before publishing this lesson.",
        "image_query": f"trading {topic.replace('-', ' ')} chart",
        "visual": {"type": "gradient", "value": visual_for_topic(topic)},
        "source": source_pdf.name,
    }


def trim_sentence(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    shortened = text[:limit].rsplit(" ", 1)[0].strip().rstrip(".,;:!?")
    return f"{shortened}."


def make_title(text: str) -> str:
    keywords = [
        ("risk", "Risk Control"),
        ("stop", "Stop Placement"),
        ("support", "Support Level"),
        ("resistance", "Resistance Level"),
        ("trend", "Trend Context"),
        ("breakout", "Breakout Context"),
        ("liquidity", "Liquidity Area"),
        ("psychology", "Trading Psychology"),
        ("position", "Position Sizing"),
        ("candle", "Candle Reading"),
    ]
    lowered = text.lower()
    for keyword, title in keywords:
        if keyword in lowered:
            return title
    words = re.findall(r"[A-Za-z][A-Za-z'-]+", text)[:5]
    title = " ".join(words).title()
    return title or "Trading Note"


def infer_topic(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["risk", "stop", "loss", "position", "size"]):
        return "risk-management"
    if any(word in lowered for word in ["emotion", "fear", "greed", "discipline", "psychology"]):
        return "psychology"
    if any(word in lowered for word in ["liquidity", "order", "volume"]):
        return "market-mechanics"
    return "technical-analysis"


def visual_for_topic(topic: str) -> str:
    return {
        "risk-management": "risk",
        "psychology": "psychology",
        "market-mechanics": "liquidity",
    }.get(topic, "support")


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def safe_print(message: object) -> None:
    text = str(message)
    try:
        print(text)
    except UnicodeEncodeError:
        encoded = text.encode(sys.stdout.encoding or "utf-8", errors="backslashreplace")
        print(encoded.decode(sys.stdout.encoding or "utf-8"))


if __name__ == "__main__":
    sys.exit(main())
