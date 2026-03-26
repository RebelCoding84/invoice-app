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
    BACKUP_DIR,
    TIMEZONE,
)
from outputs.finvoice import generate_finvoice_minimal_xml, validate_finvoice_bytes
from outputs.pdf import render_receipt_pdf
from storage import ledger
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


def _next_invoice_no(seq_path: Path) -> int:
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


def _next_receipt_no(seq_path: Path) -> int:
    """Legacy alias kept for compatibility with older imports."""
    return _next_invoice_no(seq_path)


def _build_invoice_payload(
    draft: InvoiceDraft,
    invoice_no: str,
    issue_date: datetime,
    due_date: datetime,
    totals: dict,
) -> dict:
    """Build the canonical invoice payload consumed by PDF rendering."""
    return {
        "invoice_no": invoice_no,
        "receipt_no": invoice_no,
        "issue_date": issue_date.isoformat(),
        "due_date": due_date.isoformat(),
        "customer": {
            "name": draft.customer.name,
            "email": draft.customer.email,
            "address": draft.customer.address,
            "vat_id": draft.customer.vat_id,
        },
        "line": {
            "description": draft.line.description,
            "quantity": draft.line.quantity,
            "unit_price": draft.line.unit_price,
            "vat_percent": totals["vat_percent"],
        },
        "totals": dict(totals),
        "payment_method": draft.payment_method,
        "notes": draft.notes,
        "reference": draft.notes,
        "currency": draft.currency,
    }


def _build_company_profile() -> dict[str, str]:
    """Build the canonical company profile consumed by document generators."""
    return {
        "name": COMPANY_NAME.strip(),
        "id": COMPANY_ID.strip(),
        "vat": COMPANY_VAT.strip(),
        "address": COMPANY_ADDRESS.strip(),
        "email": COMPANY_EMAIL.strip(),
        "phone": COMPANY_PHONE.strip(),
        "web": COMPANY_WEB.strip(),
    }


def _validate_company_profile(company: dict[str, str], require_finvoice: bool) -> None:
    if not (company.get("name") or "").strip():
        raise ValueError("Company name is required for PDF generation")
    if require_finvoice and not (company.get("id") or "").strip():
        raise ValueError("Company identifier is required for Finvoice generation")


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
    company = _build_company_profile()
    _validate_company_profile(company, options.generate_finvoice)
    invoice_no = _next_invoice_no(DATA_DIR / "sequence.txt")
    invoice_no_str = str(invoice_no)
    invoice_payload = _build_invoice_payload(draft, invoice_no_str, issue_date, due_date, totals)
    invoice_totals_payload = dict(totals)

    created_at = issue_date.isoformat()

    pdf_bytes = b""
    finvoice_bytes = None
    finvoice_path = None
    try:
        tmp_dir = Path("outputs")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        # Keep the on-disk PDF name aligned with the API lookup pattern.
        temp_pdf_path = tmp_dir / f"receipt_{invoice_no:06d}.pdf"
        render_receipt_pdf(str(temp_pdf_path), invoice_payload, company)
        final_pdf_path = move_receipt_to_month(str(temp_pdf_path), base_dir="storage")
        pdf_bytes = Path(final_pdf_path).read_bytes()

        if options.generate_finvoice:
            exports_dir = (
                Path("storage")
                / f"{issue_date.year:04d}"
                / f"{issue_date.month:02d}"
                / "exports"
            )
            exports_dir.mkdir(parents=True, exist_ok=True)
            finvoice_path = exports_dir / f"finvoice_{invoice_no:06d}.xml"
            invoice_totals_payload["invoice_no"] = invoice_no_str
            finvoice_bytes = generate_finvoice_minimal_xml(
                draft, invoice_totals_payload, company
            )
            if not validate_finvoice_bytes(finvoice_bytes):
                raise ValueError("Finvoice XML validation failed")
            finvoice_path.write_bytes(finvoice_bytes)

        excel_row = ledger.append_ledger(
            str(DATA_DIR / "ledger.xlsx"),
            invoice_no_str,
            draft.customer.name,
            totals,
            draft.currency,
        )

        pdf_sha256 = ledger.compute_sha256(final_pdf_path)
        event = {
            "event_type": "SUCCESS",
            "invoice_no": invoice_no,
            "receipt_no": invoice_no,
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
            backup_target = BACKUP_DIR / f"backup_{issue_date:%Y-%m}.zip"
            include_paths = [
                str(Path("storage") / f"{issue_date:%Y-%m}"),
                str(DATA_DIR / "ledger.xlsx"),
            ]
            create_backup_zip(str(backup_target), include_paths)

        artifacts = InvoiceArtifacts(
            pdf_bytes=pdf_bytes,
            finvoice_bytes=finvoice_bytes,
            invoice_no=invoice_no_str,
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
                    "invoice_no": invoice_no,
                    "receipt_no": invoice_no,
                    "reason": str(exc),
                    "created_at": created_at,
                },
            )
        except Exception:
            logger.exception("Failed to append FAILED ledger event")
        raise
