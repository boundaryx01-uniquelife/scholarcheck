from __future__ import annotations

import re


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "연구",
    "논문",
    "자료",
    "분석",
    "관련",
}


def extract_keywords(topic: str, max_keywords: int = 8) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9가-힣][A-Za-z0-9가-힣\-+_/]*", topic.lower())
    keywords: list[str] = []

    for token in tokens:
        cleaned = token.strip("-+_/")
        if len(cleaned) < 2 or cleaned in STOPWORDS:
            continue
        if cleaned not in keywords:
            keywords.append(cleaned)

    return keywords[:max_keywords]
