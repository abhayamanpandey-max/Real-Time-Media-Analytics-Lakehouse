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
    "audience_reach": [
        "audience",
        "reach",
        "viewers",
        "rank",
        "ranking",
        "rankings",
        "top properties",
        "properties",
        "property",
        "audience share",
        "share",
        "listeners",
        "traffic",
        "uniques",
        "views",
        "platform",
        "platforms",
        "profile",
        "breakdown",
        "desktop",
        "mobile",
        "smart tv",
        "connected tv",
        "ctv",
        "overlap",
        "index",
    ],
    "ad_performance": [
        "ad categories",
        "ad category",
        "ad performance",
        "brand",
        "brands",
        "ad",
        "ads",
        "spend",
        "campaign",
        "campaigns",
        "advertiser",
        "advertisers",
        "cpm",
        "yield",
        "fill rate",
        "cost",
        "dollar",
    ],
    "engagement": [
        "watch time",
        "watch",
        "content title",
        "content titles",
        "content",
        "titles",
        "seconds",
        "engagement",
        "duration",
        "completion",
        "completion rate",
        "session",
        "retention",
        "bounce",
        "time spent",
        "active time",
        "view duration",
    ],
    "composition": [
        "demographic",
        "demographics",
        "age",
        "gender",
        "male",
        "female",
        "composition",
    ],
    "monetization": [
        "revenue",
        "arpu",
        "subscription",
        "monetize",
        "monetization",
        "billing",
        "payout",
        "earnings",
    ],
}


# Generic words get weight 1; domain-specific terms get weight 2
GENERIC_WORDS = {"audience", "reach", "viewers", "views", "share", "ad", "ads"}


def route_question(question: str) -> str:
    """
    Routes an input question to one of the 4 domain keys based on weighted keyword matching.

    Args:
        question: Natural language question string.

    Returns:
        Domain key: 'audience_reach', 'engagement', 'composition', or 'ad_performance'.
    """
    if not question or not isinstance(question, str):
        return DEFAULT_DOMAIN

    q_lower = question.lower()
    scores: Dict[str, int] = {domain: 0 for domain in DOMAIN_KEYWORDS}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            pattern = r"\b" + re.escape(kw.lower()) + r"\b"
            if re.search(pattern, q_lower):
                weight = 1 if kw in GENERIC_WORDS else 2
                scores[domain] += weight

    max_score = max(scores.values())
    if max_score > 0:
        for domain, score in scores.items():
            if score == max_score:
                return domain

    return DEFAULT_DOMAIN
