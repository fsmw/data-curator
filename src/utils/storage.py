"""Storage-related helpers for user directories."""

import re


def sanitize_username(username: str) -> str:
    """
    Normalize a username for use in filesystem paths.

    Lowercases the username and replaces any non-alphanumeric characters with underscores.
    Falls back to 'user' for empty or invalid names.
    """
    if not username:
        return "user"

    normalized = username.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = normalized.strip("_")
    return normalized or "user"
