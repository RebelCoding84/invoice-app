from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ENV_PATH = Path(".env")
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


def get_env(name: str, default: str) -> str:
    """Fetch an environment variable with a default."""
    return os.getenv(name, default)


def get_bool(name: str, default: bool) -> bool:
    """Fetch a boolean environment variable with a default."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_int(name: str, default: int) -> int:
    """Fetch an integer environment variable with a default."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


DEFAULT_LOCALE = get_env("DEFAULT_LOCALE", "fi")
DEFAULT_PROVIDER = get_env("DEFAULT_PROVIDER", "rebel")

DATA_DIR = Path(get_env("DATA_DIR", "data"))
RECEIPT_DIR = Path(get_env("RECEIPT_DIR", "receipts"))
BACKUP_DIR = Path(get_env("BACKUP_DIR", "backups"))
LOG_DIR = Path(get_env("LOG_DIR", "logs"))

TIMEZONE = get_env("TIMEZONE", "Europe/Helsinki")

BACKUP_ENABLED = get_bool("BACKUP_ENABLED", True)
BACKUP_RETENTION_DAYS = get_int("BACKUP_RETENTION_DAYS", 30)

COMPANY_NAME = get_env("COMPANY_NAME", "")
COMPANY_ID = get_env("COMPANY_ID", "")
COMPANY_VAT = get_env("COMPANY_VAT", "")
COMPANY_ADDRESS = get_env("COMPANY_ADDRESS", "")
COMPANY_EMAIL = get_env("COMPANY_EMAIL", "")
COMPANY_PHONE = get_env("COMPANY_PHONE", "")
COMPANY_WEB = get_env("COMPANY_WEB", "")
