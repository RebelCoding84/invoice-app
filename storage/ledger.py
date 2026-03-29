from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from core.models import InvoiceStatus
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


def _normalize_invoice_no(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.isdigit():
        return str(int(text))
    return text


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip())
        except ValueError:
            return None
    else:
        return None

    return parsed


def _status_from_event(event: dict[str, Any]) -> InvoiceStatus | None:
    raw_status = event.get("status")
    if isinstance(raw_status, InvoiceStatus):
        return raw_status
    if isinstance(raw_status, str) and raw_status.strip():
        try:
            return InvoiceStatus(raw_status.strip().lower())
        except ValueError:
            pass

    event_type = str(event.get("event_type") or "").strip().upper()
    if event_type == "SUCCESS":
        return InvoiceStatus.ISSUED
    if event_type == "FAILED":
        return InvoiceStatus.DRAFT
    return None


def read_invoice_lifecycle_metadata(
    invoice_no: str,
    base_dir: str | Path = "storage",
) -> dict[str, Any] | None:
    """Return the latest lifecycle event for a single invoice number."""
    normalized_invoice_no = _normalize_invoice_no(invoice_no)
    if not normalized_invoice_no:
        return None

    ledger_root = Path(base_dir)
    if not ledger_root.exists():
        return None

    latest_event: dict[str, Any] | None = None
    latest_key: tuple[datetime, str, int] | None = None

    for ledger_path in ledger_root.rglob("ledger_*.jsonl"):
        with ledger_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle):
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_invoice_no = _normalize_invoice_no(
                    event.get("invoice_no") or event.get("receipt_no")
                )
                if event_invoice_no != normalized_invoice_no:
                    continue

                status = _status_from_event(event)
                if status is None:
                    continue

                status_changed_at = _parse_datetime(
                    event.get("status_changed_at") or event.get("created_at")
                )
                created_at = _parse_datetime(event.get("created_at"))
                sort_key = (
                    status_changed_at or created_at or datetime.min,
                    str(ledger_path),
                    line_no,
                )
                if latest_key is None or sort_key >= latest_key:
                    latest_key = sort_key
                    latest_event = {
                        "invoice_no": event_invoice_no,
                        "event_type": str(event.get("event_type") or ""),
                        "status": status,
                        "status_changed_at": status_changed_at or created_at,
                        "created_at": created_at,
                    }

    return latest_event
