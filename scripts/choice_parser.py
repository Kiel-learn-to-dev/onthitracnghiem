"""Extract A-D answer choices embedded in imported PDF question text."""

from __future__ import annotations

from dataclasses import dataclass
import re


CHOICE_LABEL = re.compile(r"(?i)(?<!\S)([a-h])\s*[).:]\s*")
CHOICE_SEQUENCES = (("a", "b", "c", "d"), ("e", "f", "g", "h"))


@dataclass(frozen=True)
class ChoiceParseResult:
    question: str
    choices: list[str]
    reason: str | None

    @property
    def is_complete(self) -> bool:
        return self.reason is None


def parse_question_choices(raw_question: str) -> ChoiceParseResult:
    """Split a source question into its stem and exactly four A-D choices.

    The source text is preserved unchanged elsewhere. This parser never fills a
    missing choice: callers must send incomplete records to review.
    """
    matches = [
        match
        for match in CHOICE_LABEL.finditer(raw_question)
        if _is_choice_label(raw_question, match.start(1))
    ]
    found_labels = [match.group(1).lower() for match in matches]
    expected_labels = next(
        (sequence for sequence in CHOICE_SEQUENCES if sequence[0] in found_labels),
        CHOICE_SEQUENCES[0],
    )
    missing = [label.upper() for label in expected_labels if label not in found_labels]
    duplicates = sorted({label.upper() for label in found_labels if found_labels.count(label) > 1})

    if missing or duplicates:
        details: list[str] = []
        if missing:
            details.append(f"missing choices: {', '.join(missing)}")
        if duplicates:
            details.append(f"duplicate labels: {', '.join(duplicates)}")
        return ChoiceParseResult(raw_question.strip(), [], "; ".join(details))

    if found_labels != list(expected_labels):
        return ChoiceParseResult(raw_question.strip(), [], "choices are not ordered")

    question = raw_question[: matches[0].start()].strip()
    choices = [
        raw_question[match.end() : matches[index + 1].start() if index + 1 < len(matches) else None].strip()
        for index, match in enumerate(matches)
    ]
    empty = [label.upper() for label, choice in zip(expected_labels, choices) if not choice]
    if empty:
        return ChoiceParseResult(raw_question.strip(), [], f"empty choices: {', '.join(empty)}")
    if not question:
        return ChoiceParseResult(raw_question.strip(), [], "missing question stem")

    return ChoiceParseResult(question, choices, None)


def extract_question_stem(raw_question: str) -> str:
    """Return text before the first credible answer marker, if present."""
    matches = [
        match
        for match in CHOICE_LABEL.finditer(raw_question)
        if _is_choice_label(raw_question, match.start(1))
    ]
    return raw_question[: matches[0].start()].strip() if matches else raw_question.strip()


def _is_choice_label(text: str, label_start: int) -> bool:
    """Reject a variable such as ``b)`` inside a C expression as a label."""
    prefix = text[:label_start].rstrip()
    if not prefix or prefix.endswith("\n"):
        return True
    return prefix[-1] not in "=&|*/+-<>!([{,"
