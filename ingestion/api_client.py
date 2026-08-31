"""
ingestion/api_client.py

Config-driven HTTP client for the analytics API.
In dev: points to the local Mock API (FastAPI).
In prod: points to the real analytics API.
Swapping environments is a config change only - this code never changes.

Retry strategy: up to 3 attempts with exponential backoff (1s, 2s, 4s)
on ConnectionError, Timeout, or 5xx responses.
"""

import json
import logging
import time

import requests

logger = logging.getLogger(__name__)


class ApiClientError(Exception):
    """Custom exception for API client errors."""
    pass


def fetch_all_events(config: dict) -> tuple[list[dict], bool]:
    """
    Fetch all paginated events from the API.

    Args:
        config: Loaded configuration dictionary containing API settings.

    Returns:
        A tuple of (events_list, fallback_used_flag).
        - events_list: List of raw event dicts, each tagged with '_ingestion_source'.
        - fallback_used_flag: True if fallback in-memory generator was used, False if live API was queried.
    """
    api_config = config.get("api", {})
    base_url = api_config.get("base_url")
    token = api_config.get("token")
    page_size = api_config.get("page_size", 100)
    max_pages = api_config.get("max_pages", 1000)

    if not base_url or not token:
        raise ApiClientError("Missing 'base_url' or 'token' in API config.")

    headers = {"Authorization": f"Bearer {token}"}
    all_events = []
    page = 1
    has_next = True

    while has_next and page <= max_pages:
        url = f"{base_url}/events?page={page}&page_size={page_size}"
        
        max_retries = 3
        backoff_times = [1, 2, 4]
        success = False

        for attempt in range(max_retries + 1):
            try:
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code >= 500:
                    raise requests.exceptions.HTTPError(f"Server error: {response.status_code}")
                if response.status_code == 401:
                    raise ApiClientError(f"Unauthorized: Invalid token (status {response.status_code})")

                response.raise_for_status()

                data = response.json()
                events = data.get("events", [])
                for evt in events:
                    evt["_ingestion_source"] = "live"
                all_events.extend(events)
                has_next = data.get("has_next", False)

                logger.debug(f"Fetched page {page} with {len(events)} events.")
                success = True
                break

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
                if attempt < max_retries:
                    sleep_time = backoff_times[attempt]
                    logger.warning(f"Error fetching page {page}: {e}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"FALLBACK_USED=true: API endpoint {url} unreachable after {max_retries} retries ({e}). Falling back to synthetic event generator for in-memory generation.")
                    # Fallback: Generate 500 synthetic events directly in memory so Bronze ingestion never fails
                    from generator.synthetic_event_producer import produce_event
                    synthetic_events = []
                    for _ in range(500):
                        evt = produce_event(producer=None, topic="", config=config)
                        evt["_ingestion_source"] = "fallback"
                        synthetic_events.append(evt)
                    return synthetic_events, True
            except ApiClientError:
                raise
            except Exception as e:
                raise ApiClientError(f"Unexpected error on page {page}: {e}")

        if not success:
            break

        page += 1

    logger.info(f"Finished fetching {len(all_events)} total events from live API (FALLBACK_USED=false).")
    return all_events, False
