"""Transparent first-pass difficulty tagging for source questions."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class TagResult:
    difficulty: str
    status: str
    reason: str


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")


def classify_question(
    question: str, source_filename: str, existing_difficulty: str | None = None
) -> TagResult:
    """Classify by cognitive load and programming concepts, retaining trusted source tags."""
    if existing_difficulty:
        return TagResult(existing_difficulty, "source_verified", "Mức độ đã có trong ngân hàng câu hỏi gốc.")

    text = _fold(question)
    has_code = any(token in text for token in ("#include", "printf", "scanf", "int main", "for(", "while(", "do {"))
    advanced_hits = sum(
        token in text
        for token in (
            "con tro", "pointer", "struct", "cau truc", "mang", "chuoi", "file", "macro",
            "de quy", "recursion", "cap phat", "linked", "danh sach", "union", "bit",
        )
    )
    long_trace = len(text) >= 850 or (has_code and len(text) >= 500)
    source = _fold(source_filename)

    if long_trace or (has_code and advanced_hits >= 2):
        return TagResult("Rất khó", "rule_based", "Code tracing dài hoặc kết hợp từ hai chủ đề nâng cao.")
    if "de 2" in source:
        return TagResult("Khó", "rule_based", "Câu thuộc đề thi kết thúc học phần.")
    if advanced_hits >= 2 or (has_code and advanced_hits >= 1):
        return TagResult("Khó", "rule_based", "Có code tracing hoặc kết hợp khái niệm nâng cao.")
    if has_code or advanced_hits == 1 or len(text) >= 300:
        return TagResult("Vừa", "rule_based", "Cần áp dụng một khái niệm hoặc theo dõi biểu thức ngắn.")
    return TagResult("Dễ", "rule_based", "Câu nhận biết hoặc thao tác cú pháp/khái niệm trực tiếp.")
