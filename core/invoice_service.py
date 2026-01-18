from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from config import (
    BACKUP_ENABLED,
    COMPANY_ADDRESS,
    COMPANY_EMAIL,
    COMPANY_ID,
    COMPANY_NAME,
    COMPANY_PHONE,
    COMPANY_VAT,
    COMPANY_WEB,
    DATA_DIR,
    TIMEZONE,
)
from outputs.finvoice import generate_finvoice_minimal_xml, validate_finvoice_bytes
from outputs.pdf import render_receipt_pdf
from storage import excel, ledger
from storage.archive_manager import move_receipt_to_month
from storage.backup_manager import create_backup_zip
from utils.atomic import atomic_write_text
from utils.money import compute_totals

from core.models import InvoiceArtifacts, InvoiceDraft, InvoiceOptions, InvoiceResult


def _get_now() -> datetime:
    try:
        tz = ZoneInfo(TIMEZONE)
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz=tz)


def _next_receipt_no(seq_path: Path) -> int:
    seq_path.parent.mkdir(parents=True, exist_ok=True)
    current = 0
    if seq_path.exists():
        try:
            current = int(seq_path.read_text(encoding="utf-8").strip() or 0)
        except ValueError:
            current = 0
    new_value = current + 1
    atomic_write_text(str(seq_path), f"{new_value}\n", encoding="utf-8")
    return new_value


def create_invoice(draft: InvoiceDraft, options: InvoiceOptions) -> InvoiceResult:
    """Create invoice artifacts and persist ledger entries using existing formats."""
    logger = logging.getLogger("invoice_app")
    quantity = draft.line.quantity
    unit_price = draft.line.unit_price

    if quantity <= Decimal("0"):
        raise ValueError("Quantity must be greater than 0")
    if unit_price < Decimal("0"):
        raise ValueError("Unit price must be zero or positive")

    issue_date = draft.issue_date or _get_now()
    due_date = draft.due_date or issue_date + timedelta(days=14)
    totals = compute_totals(quantity, unit_price, draft.line.vat_percent)
    totals_payload = dict(totals)

    receipt_no = _next_receipt_no(DATA_DIR / "sequence.txt")
    created_at = issue_date.isoformat()

    payload = {
        "receipt_no": receipt_no,
        "date": created_at,
        "created_at": created_at,
        "due_date": due_date.isoformat(),
        "customer": draft.customer.name,
        "customer_name": draft.customer.name,
        "reference": draft.notes,
        "pay_method": draft.payment_method,
        "item": draft.line.description,
        "qty": str(quantity),
        "unit_price": str(unit_price),
        "vat_pct": str(totals["vat_percent"]),
        "subtotal": str(totals["subtotal_ex_vat"]),
        "vat_amount": str(totals["vat_amount"]),
        "total": str(totals["total_inc_vat"]),
        "currency": draft.currency,
        "items": [
            {
                "name": draft.line.description,
                "qty": str(quantity),
                "unit_price": str(unit_price),
            }
        ],
    }
    company = {
        "name": COMPANY_NAME,
        "address": COMPANY_ADDRESS,
        "id": COMPANY_ID,
        "vat": COMPANY_VAT,
        "email": COMPANY_EMAIL,
        "phone": COMPANY_PHONE,
        "web": COMPANY_WEB,
    }

    pdf_bytes = b""
    finvoice_bytes = None
    finvoice_path = None
    try:
        tmp_dir = Path("outputs")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        temp_pdf_path = tmp_dir / f"receipt_{receipt_no:06d}_tmp.pdf"
        render_receipt_pdf(str(temp_pdf_path), payload, company)
        final_pdf_path = move_receipt_to_month(str(temp_pdf_path), issue_date, receipt_no)
        pdf_bytes = Path(final_pdf_path).read_bytes()

        if options.generate_finvoice:
            exports_dir = (
                Path("storage")
                / f"{issue_date.year:04d}"
                / f"{issue_date.month:02d}"
                / "exports"
            )
            exports_dir.mkdir(parents=True, exist_ok=True)
            finvoice_path = exports_dir / f"finvoice_{receipt_no:06d}.xml"
            totals_payload["invoice_no"] = receipt_no
            finvoice_bytes = generate_finvoice_minimal_xml(draft, totals_payload, company)
            if not validate_finvoice_bytes(finvoice_bytes):
                raise ValueError("Finvoice XML validation failed")
            finvoice_path.write_bytes(finvoice_bytes)

        excel_row = excel.save_row_to_excel(
            str(DATA_DIR / "ledger.xlsx"),
            {
                "receipt_no": receipt_no,
                "created_at": created_at,
                "customer": draft.customer.name,
                "item": draft.line.description,
                "qty": float(quantity),
                "unit_price": float(unit_price),
                "vat_pct": float(totals["vat_percent"]),
                "subtotal": float(totals["subtotal_ex_vat"]),
                "vat": float(totals["vat_amount"]),
                "total": float(totals["total_inc_vat"]),
                "pay_method": draft.payment_method,
                "note": draft.notes,
                "provider": "local",
                "pdf_path": final_pdf_path,
            },
        )

        pdf_sha256 = ledger.compute_sha256(final_pdf_path)
        event = {
            "event_type": "SUCCESS",
            "receipt_no": receipt_no,
            "pdf_path": final_pdf_path,
            "pdf_sha256": pdf_sha256,
            "excel_row": excel_row,
            "created_at": created_at,
        }
        if finvoice_path:
            event["finvoice_path"] = str(finvoice_path)
            event["finvoice_sha256"] = ledger.compute_sha256(str(finvoice_path))
        ledger.append_event(issue_date, event)

        if options.enable_backup and BACKUP_ENABLED:
            create_backup_zip(issue_date)

        artifacts = InvoiceArtifacts(
            pdf_bytes=pdf_bytes,
            finvoice_bytes=finvoice_bytes,
            invoice_no=str(receipt_no),
        )
        return InvoiceResult(
            totals=totals,
            artifacts=artifacts,
            paths={
                "pdf_path": final_pdf_path,
                "finvoice_path": str(finvoice_path) if finvoice_path else None,
                "excel_row": excel_row,
            },
        )
    except Exception as exc:
        try:
            ledger.append_event(
                issue_date,
                {
                    "event_type": "FAILED",
                    "receipt_no": receipt_no,
                    "reason": str(exc),
                    "created_at": created_at,
                },
            )
        except Exception:
            logger.exception("Failed to append FAILED ledger event")
        raise
