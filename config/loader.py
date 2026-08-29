"""
config/loader.py

Loads environment-specific YAML config. All jobs and services read config
through this module. Swapping dev to prod is a single env var change:
  set LAKEHOUSE_ENV=prod

Supports ${ENV_VAR} substitution in YAML values (for prod secrets).
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

# Canonical allowed values - defined here once, imported everywhere.
# Silver DQ rules validate against these same lists.
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

_CONFIG_DIR = Path(__file__).parent


def _resolve_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} tokens with environment variable values."""
    pattern = re.compile(r"\$\{([^}]+)\}")

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        resolved = os.environ.get(var_name)
        if resolved is None:
            raise EnvironmentError(
                f"Config references environment variable '{var_name}' but it is not set."
            )
        return resolved

    return pattern.sub(replacer, value)


def _resolve_recursive(obj: Any) -> Any:
    """Recursively resolve ${ENV_VAR} tokens in all string values."""
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    if isinstance(obj, dict):
        return {k: _resolve_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_recursive(item) for item in obj]
    return obj


def load_config(env: str | None = None) -> dict[str, Any]:
    """
    Load and return the config dict for the given environment.

    Args:
        env: 'dev' or 'prod'. If None, reads LAKEHOUSE_ENV env var (default: 'dev').

    Returns:
        Parsed config dict with ${ENV_VAR} tokens resolved.

    Raises:
        FileNotFoundError: if the config file does not exist.
        EnvironmentError: if a required env var is not set.
    """
    if env is None:
        env = os.environ.get("LAKEHOUSE_ENV", "dev")

    config_path = _CONFIG_DIR / f"{env}.yml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            f"For prod, copy config/prod.yml.example to config/prod.yml and fill in values."
        )

    with config_path.open() as fh:
        raw = yaml.safe_load(fh)

    # Only resolve env vars for prod (dev has literal values).
    if env == "prod":
        config = _resolve_recursive(raw)
    else:
        config = raw

    # Allow dynamic override of API base URL via API_BASE_URL env var (e.g. EC2 public IP/domain)
    if "API_BASE_URL" in os.environ and "api" in config:
        config["api"]["base_url"] = os.environ["API_BASE_URL"].rstrip("/")

    return config


def get_full_table_name(config: dict, layer: str, table_key: str) -> str:
    """
    Build the fully-qualified Delta table name: catalog.schema.table.

    Args:
        config: Loaded config dict.
        layer: Schema layer key, e.g. 'bronze', 'silver', 'gold'.
        table_key: Key from config['databricks']['tables'], e.g. 'bronze_events'.

    Returns:
        Fully-qualified name, e.g. 'analytics_dev.bronze.audience_events'.
    """
    catalog = config["databricks"]["catalog"]
    schema = config["databricks"]["schemas"][layer]
    table = config["databricks"]["tables"][table_key]
    return f"{catalog}.{schema}.{table}"
