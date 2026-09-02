"""
tests/test_router.py

Unit tests for supervisor keyword-based question router.
Validates routing logic against domain question lists.
"""

import pytest
from supervisor.router import DEFAULT_DOMAIN, route_question


@pytest.mark.parametrize(
    "question,expected_domain",
    [
        # Audience Reach Domain
        (
            "Which property had the highest total audience in the most recent monthly period?",
            "audience_reach",
        ),
        (
            "What are the top 5 properties by audience share in the US for Q3?",
            "audience_reach",
        ),
        (
            "Which media property had the most viewers last month?",
            "audience_reach",
        ),
        (
            "Who were the bottom 10 properties in total audience for the yearly period?",
            "audience_reach",
        ),
        (
            "What is the average total audience for the top 3 properties monthly?",
            "audience_reach",
        ),
        # Engagement Domain
        (
            "What is the average watch time per session for property ABC?",
            "engagement",
        ),
        (
            "Which property has the highest user retention and engagement rate?",
            "engagement",
        ),
        (
            "Show me the average session duration across platforms",
            "engagement",
        ),
        (
            "What is the video completion rate for desktop viewers?",
            "engagement",
        ),
        (
            "How does user active time compare across weekly periods?",
            "engagement",
        ),
        # Composition Domain
        (
            "What is the audience profile breakdown by platform for property XYZ?",
            "composition",
        ),
        (
            "Which region has the highest concentration of mobile users for property ABC?",
            "composition",
        ),
        (
            "Compare the desktop vs mobile audience for property LMN in Europe.",
            "composition",
        ),
        (
            "What is the audience overlap index between property ABC and XYZ?",
            "composition",
        ),
        (
            "What is the demographic breakdown of Smart TV viewers?",
            "composition",
        ),
        # Monetization Domain
        (
            "What is the total ad revenue for property XYZ this quarter?",
            "monetization",
        ),
        (
            "Which region generated the highest average CPM?",
            "monetization",
        ),
        (
            "Show ARPU trends and subscription billing figures by region",
            "monetization",
        ),
        (
            "What is the ad fill rate and revenue yield for property PQR?",
            "monetization",
        ),
        (
            "How much earnings were generated per dollar spent on ads?",
            "monetization",
        ),
    ],
)
def test_route_question(question: str, expected_domain: str):
    """Verifies that sample domain questions route to their expected domain keys."""
    routed_domain = route_question(question)
    assert routed_domain == expected_domain, f"Expected '{expected_domain}', got '{routed_domain}' for: '{question}'"


def test_route_question_fallback():
    """Verifies that unclassified questions or invalid inputs fallback to default domain."""
    assert route_question("Random generic sentence without domain keywords") == DEFAULT_DOMAIN
    assert route_question("") == DEFAULT_DOMAIN
    assert route_question(None) == DEFAULT_DOMAIN
