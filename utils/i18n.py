from __future__ import annotations

import json
from pathlib import Path


def load_locale(locale: str, locales_dir: str = "locales") -> dict:
    """Load a locale JSON file with fallback to Finnish ("fi")."""
    locales_path = Path(locales_dir)
    primary = locales_path / f"{locale}.json"
    fallback = locales_path / "fi.json"

    path = primary if primary.exists() else fallback
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def t(key: str, lang: dict) -> str:
    """Translate a key using the provided language dict, fallback to key."""
    return lang.get(key, key)
