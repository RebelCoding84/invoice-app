from __future__ import annotations

import os
from pathlib import Path


def atomic_write_bytes(path: str, data: bytes) -> None:
    """Atomically write bytes and swallow fsync errors for Windows compatibility."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass
    os.replace(tmp, target)


def atomic_write_text(path: str, text: str, encoding: str = "utf-8") -> None:
    """Atomically write text and swallow fsync errors for Windows compatibility."""
    data = text.encode(encoding)
    atomic_write_bytes(path, data)
