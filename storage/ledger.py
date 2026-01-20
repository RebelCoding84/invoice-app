from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path

from storage.excel import write_ledger_xlsx


def append_ledger(
    path: str,
    invoice_no: str,
    customer_name: str,
    totals: dict,
    currency: str,
) -> str:
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "invoice_no": invoice_no,
        "customer_name": customer_name,
        "subtotal_ex_vat": totals.get("subtotal_ex_vat"),
        "vat_amount": totals.get("vat_amount"),
        "total_inc_vat": totals.get("total_inc_vat"),
        "currency": currency,
    }
    write_ledger_xlsx(path, row)
    return path


def compute_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_event(issue_date: datetime, event: dict) -> str:
    month_key = issue_date.strftime("%Y-%m")
    meta_dir = Path("storage") / month_key / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = meta_dir / f"ledger_{month_key}.jsonl"
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False))
        handle.write("\n")
    return str(ledger_path)
