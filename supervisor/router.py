"""
supervisor/router.py

Keyword-based routing module for mapping analytical questions to one of 4 domain keys:
  - audience_reach
  - engagement
  - composition
  - monetization

Uses word-boundary matching to prevent sub-word false positives.
"""

import re
from typing import Dict, List

DEFAULT_DOMAIN = "audience_reach"

# Configurable keyword dictionary mapping domain keys to lowercase keywords/phrases.
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "monetization": [
        "revenue",
        "cpm",
        "arpu",
        "ad",
        "ads",
        "yield",
        "fill rate",
        "subscription",
        "monetize",
        "monetization",
        "billing",
        "payout",
        "cost",
        "dollar",
        "earnings",
        "watch time",
        "watch",
        "content title",
        "content titles",
        "content",
        "titles",
    ],
    "composition": [
        "composition",
        "demographic",
        "demographics",
        "profile",
        "overlap",
        "platform",
        "desktop",
        "mobile",
        "smart tv",
        "connected tv",
        "ctv",
        "device",
        "region",
    ],
    "engagement": [
        "engagement",
        "duration",
        "watch time",
        "completion",
        "completion rate",
        "session",
        "retention",
        "bounce",
        "time spent",
        "frequency",
        "active time",
        "view duration",
    ],
    "audience_reach": [
        "audience",
        "reach",
        "viewers",
        "rank",
        "ranking",
        "rankings",
        "top properties",
        "audience share",
        "share",
        "listeners",
        "traffic",
        "uniques",
        "views",
    ],
}


def route_question(question: str) -> str:
    """
    Routes an input question to one of the 4 domain keys based on word-boundary keyword matching.

    Args:
        question: Natural language question string.

    Returns:
        Domain key: 'audience_reach', 'engagement', 'composition', or 'monetization'.
    """
    if not question or not isinstance(question, str):
        return DEFAULT_DOMAIN

    q_lower = question.lower()
    scores: Dict[str, int] = {domain: 0 for domain in DOMAIN_KEYWORDS}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            pattern = r"\b" + re.escape(kw.lower()) + r"\b"
            if re.search(pattern, q_lower):
                scores[domain] += 1

    max_score = max(scores.values())
    if max_score > 0:
        for domain, score in scores.items():
            if score == max_score:
                return domain

    return DEFAULT_DOMAIN
