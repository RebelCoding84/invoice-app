from __future__ import annotations

import re
from pathlib import Path

_ALLOWED_RE = re.compile(r"[^a-zA-Z0-9\-_\s]+")
_WHITESPACE_RE = re.compile(r"\s+")


def sanitize_filename(value: str, max_len: int = 80) -> str:
    """Return a filesystem-friendly filename with a conservative ASCII set."""
    cleaned = _ALLOWED_RE.sub("_", value)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    if not cleaned:
        cleaned = "unknown"
    return cleaned[:max_len]


def safe_join(base_dir: str, *parts: str) -> str:
    """Join path parts under base_dir and forbid escaping the base directory."""
    base = Path(base_dir).resolve()
    candidate = base.joinpath(*parts).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError("Resolved path escapes base directory") from exc
    return str(candidate)
