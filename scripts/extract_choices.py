"""Extract A-D choice text from raw imported question evidence.

The source PDFs were initially preserved verbatim so that OCR mistakes remain
auditable.  This module performs only a conservative split: a question is
updated when it contains exactly one ordered set of four A-D option markers.
Anything incomplete is deliberately left for source-page review.
"""

from __future__ import annotations

import json
import re


OPTION_MARKER = re.compile(r"(?im)^\s*([a-h])\s*[\).:]\s*")
SOURCE_FOOTER = re.compile(
    r"(?im)^Downloaded by .*?$|^lOMoARcPSD\|.*?$",
)


def extract_four_choices(raw_question: str) -> list[str] | None:
    """Return four choices from an ordered A-D or E-H source-label set.

    A few pages use E-H because the original document restarted its visual
    option labels after a page break.  They still represent the first through
    fourth alternative and are normalized to the database's A-D positions.
    """
    cleaned = SOURCE_FOOTER.sub("", raw_question or "")
    matches = list(OPTION_MARKER.finditer(cleaned))
    labels = [match.group(1).lower() for match in matches]
    if len(matches) != 4 or labels not in (list("abcd"), list("efgh")):
        return None
    choices: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        choice = cleaned[match.end() : end].strip()
        if not choice:
            return None
        choices.append(choice)
    return choices


def choices_json(raw_question: str) -> str | None:
    """Serialize conservative extraction for SQLite storage."""
    choices = extract_four_choices(raw_question)
    return json.dumps(choices, ensure_ascii=False) if choices else None
