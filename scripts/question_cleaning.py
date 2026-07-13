"""Safe display normalization for imported multiple-choice questions."""

from __future__ import annotations

import re
import unicodedata

from scripts.choice_parser import extract_question_stem, parse_question_choices


QUESTION_NUMBER = re.compile(r"^\s*(?:câu|cau)\s*(?:hỏi|hoi)?\s*\d+\s*[.:)]\s*", re.IGNORECASE)
SOURCE_FOOTER = re.compile(r"(?im)^\s*(?:downloaded by|lomoarcsd\|).*$")
TRAILING_LABEL = re.compile(r"\n\s*[a-d]\s*$", re.IGNORECASE)
def clean_question_text(raw_question: str) -> str:
    """Return only a question stem, without source numbering or duplicated choices."""
    parsed = parse_question_choices(raw_question)
    # OCR occasionally drops the delimiter of a later choice (for example
    # ``d0...65535``).  The first credible ``a)`` marker is still enough to
    # separate the display stem; completeness is only required when parsing
    # choices themselves.
    question = parsed.question if parsed.is_complete else extract_question_stem(raw_question)
    question = SOURCE_FOOTER.sub("", question)
    question = QUESTION_NUMBER.sub("", question)
    question = TRAILING_LABEL.sub("", question)
    question = re.sub(r"\n{3,}", "\n\n", question)
    return question.strip()


def clean_choice_text(choice: str) -> str:
    """Normalize spacing without changing source code or mathematical notation."""
    return re.sub(r"\s+", " ", choice).strip()


def is_safe_for_release(text: str) -> bool:
    """Reject text with OCR replacement artefacts that would mislead learners."""
    if "\ufffd" in text or "??" in text:
        return False
    return not bool(re.search(r"[A-Za-z]\?[A-Za-z]", text))


def comparable_question_key(question: str) -> str:
    """Create a forgiving key used only to find likely clean duplicates."""
    normalized = unicodedata.normalize("NFD", clean_question_text(question))
    normalized = "".join(character for character in normalized if unicodedata.category(character) != "Mn")
    normalized = normalized.casefold()
    for broken, corrected in {"dur": "du", "dir": "du", "xur": "xu", "ngur": "ngu", "den": "den"}.items():
        normalized = normalized.replace(broken, corrected)
    return re.sub(r"[^a-z0-9]", "", normalized)
