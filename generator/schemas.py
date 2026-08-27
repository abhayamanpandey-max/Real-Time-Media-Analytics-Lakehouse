"""
generator/schemas.py

Canonical Pydantic v2 schemas for synthetic audience events.
These models define the contract between the generator, Kafka, and the Mock API.
All downstream layers (bronze, silver) derive their expected shape from AudienceEvent.

Do NOT add business logic here - pure data shapes and basic validators only.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator

# ── Allowed value sets (single source of truth) ─────────────────────────────
# These are the authoritative enums. Silver DQ rules import and validate
# against these exact lists. If you need to add a value, add it here first.
ALLOWED_PLATFORMS: list[str] = [
    "web",
    "mobile_app",
    "connected_tv",
    "smart_tv",
    "streaming_device",
    "desktop_app",
]

ALLOWED_CATEGORIES: list[str] = [
    "news",
    "sports",
    "entertainment",
    "lifestyle",
    "documentary",
    "kids",
    "finance",
    "tech",
]


class AudienceEvent(BaseModel):
    """
    A single audience measurement event.

    Grain: one row per (property_id, event_date, platform, geography_id).
    This grain is intentional: audience_value is the measured audience for
    exactly that property on that date, on that platform, in that geography.
    Aggregating to 'total property audience' requires SUM across platform and
    geography dimensions - never assume a single row per property per day.
    """

    event_id: str = Field(description="UUID v4 uniquely identifying this event record.")
    property_id: str = Field(description="Stable identifier for the media property. Format: PROP_NNN.")
    property_name: str = Field(description="Human-readable name of the media property.")
    geography_id: str = Field(description="Stable identifier for the geography. Format: GEO_NNN.")
    geography_name: str = Field(description="Human-readable geography name.")
    platform: str = Field(description=f"Distribution platform. Allowed: {ALLOWED_PLATFORMS}.")
    category: str = Field(description=f"Content category. Allowed: {ALLOWED_CATEGORIES}.")
    event_date: str = Field(description="Measurement date in ISO 8601 format: YYYY-MM-DD.")
    audience_value: int = Field(ge=0, description="Non-negative measured audience size.")
    ingested_at: str = Field(description="ISO 8601 UTC datetime when the event was produced.")

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        normalised = v.strip().lower()
        if normalised not in ALLOWED_PLATFORMS:
            raise ValueError(f"platform '{v}' not in allowed set: {ALLOWED_PLATFORMS}")
        return normalised

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        normalised = v.strip().lower()
        if normalised not in ALLOWED_CATEGORIES:
            raise ValueError(f"category '{v}' not in allowed set: {ALLOWED_CATEGORIES}")
        return normalised

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, v: str) -> str:
        date.fromisoformat(v)  # Raises ValueError if unparseable.
        return v


class AudienceEventPage(BaseModel):
    """Paginated API response wrapper returned by the Mock API."""

    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_events: int = Field(ge=0)
    has_next: bool
    events: list[AudienceEvent]
