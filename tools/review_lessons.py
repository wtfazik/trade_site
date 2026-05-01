#!/usr/bin/env python3
"""Quality checks for active Trading Reels AI lessons."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSONS_FILE = ROOT / "content" / "lessons.json"


def main() -> int:
    lessons = json.loads(LESSONS_FILE.read_text(encoding="utf-8"))
    errors = []
    for index, lesson in enumerate(lessons, start=1):
        prefix = f"lesson {index} ({lesson.get('id', 'missing-id')})"
        title = str(lesson.get("title", ""))
        if has_cyrillic(title):
            errors.append(f"{prefix}: title should stay English")
        for field in ["hook", "short_text", "simple_explanation", "example"]:
            value = str(lesson.get(field, ""))
            if not value:
                errors.append(f"{prefix}: missing {field}")
            if not has_cyrillic(value):
                errors.append(f"{prefix}: {field} should be Russian")
            if len(value) > 520:
                errors.append(f"{prefix}: {field} is too long")
            if forbidden(value):
                errors.append(f"{prefix}: {field} contains forbidden content")
        if not lesson.get("book_media"):
            errors.append(f"{prefix}: missing book_media")

    if errors:
        safe_print("Lesson review failed:")
        for error in errors:
            safe_print(f"- {error}")
        return 1

    safe_print(f"Lesson review passed: {len(lessons)} lessons")
    return 0


def has_cyrillic(value: str) -> bool:
    return bool(re.search(r"[А-Яа-яЁё]", value))


def forbidden(value: str) -> bool:
    return bool(re.search(r"sk-|AIza|hf_|tgp_|\.pdf|content/books|guaranteed|100%|always profitable", value, re.I))


def safe_print(message: object) -> None:
    text = str(message)
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, errors="backslashreplace").decode(encoding))


if __name__ == "__main__":
    sys.exit(main())
