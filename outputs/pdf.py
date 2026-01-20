"""PDF rendering helpers for receipts and invoices."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _format_totals(totals: Any) -> str:
    if totals is None:
        return "N/A"
    if isinstance(totals, dict):
        parts = []
        for key, value in totals.items():
            parts.append(f"{key}: {value}")
        return ", ".join(parts) if parts else "N/A"
    return str(totals)


def render_receipt_pdf(output_path: str, payload: dict, company: dict) -> bytes:
    """Render a minimal receipt/invoice PDF and return its bytes."""
    payload = payload or {}
    company = company or {}

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    title = "Receipt / Invoice"
    company_name = company.get("name") or company.get("company_name") or "N/A"
    invoice_no = payload.get("invoice_no") or payload.get("invoice_number") or "N/A"
    customer = payload.get("customer") or {}
    customer_name = (
        customer.get("name") if isinstance(customer, dict) else str(customer)
    ) or "N/A"
    totals = _format_totals(payload.get("totals") or payload.get("total"))

    y = height - 72
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, title)
    y -= 36

    c.setFont("Helvetica", 12)
    c.drawString(72, y, f"Company: {company_name}")
    y -= 18
    c.drawString(72, y, f"Invoice #: {invoice_no}")
    y -= 18
    c.drawString(72, y, f"Customer: {customer_name}")
    y -= 18
    c.drawString(72, y, f"Totals: {totals}")

    c.showPage()
    c.save()

    return path.read_bytes()
