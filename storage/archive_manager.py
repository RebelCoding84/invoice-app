from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil


def move_receipt_to_month(src_path: str, base_dir: str = "receipts") -> str:
    source = Path(src_path)
    if not source.exists():
        raise FileNotFoundError(f"Receipt source not found: {src_path}")

    base_path = Path(base_dir)
    month_folder = datetime.now().strftime("%Y-%m")
    if base_path.name == "receipts":
        month_dir = base_path / month_folder
    else:
        month_dir = base_path / month_folder / "receipts"
    month_dir.mkdir(parents=True, exist_ok=True)
    destination = month_dir / source.name
    shutil.move(str(source), destination)
    return str(destination)
