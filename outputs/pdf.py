"""PDF rendering helpers for receipts and invoices."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _format_value(value: Any) -> str:
    if value is None or value == "":
        return "N/A"
    return str(value)


def _format_amount(value: Any) -> str:
    if value is None or value == "":
        return "N/A"
    try:
        return f"{value:.2f}"
    except (TypeError, ValueError):
        return str(value)


def _format_date(value: Any) -> str:
    if value is None or value == "":
        return "N/A"
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date().isoformat()
        except ValueError:
            return value
    return str(value)


def _coerce_company(company: dict[str, Any]) -> dict[str, Any]:
    company = company or {}
    return {
        "name": company.get("name") or company.get("company_name") or company.get("COMPANY_NAME") or "",
        "id": company.get("id") or company.get("company_id") or company.get("COMPANY_ID") or "",
        "vat": company.get("vat") or company.get("company_vat") or company.get("COMPANY_VAT") or "",
        "address": company.get("address") or company.get("company_address") or company.get("COMPANY_ADDRESS") or "",
        "email": company.get("email") or company.get("company_email") or company.get("COMPANY_EMAIL") or "",
        "phone": company.get("phone") or company.get("company_phone") or company.get("COMPANY_PHONE") or "",
        "web": company.get("web") or company.get("company_web") or company.get("COMPANY_WEB") or "",
    }


def _coerce_customer(payload: dict[str, Any]) -> dict[str, Any]:
    customer = payload.get("customer")
    if isinstance(customer, dict):
        return customer
    return {
        "name": payload.get("customer_name") or (str(customer) if customer else ""),
        "address": payload.get("customer_address") or "",
        "email": payload.get("customer_email") or payload.get("email") or "",
        "vat_id": payload.get("customer_vat_id") or payload.get("vat_id") or "",
    }


def _coerce_line(payload: dict[str, Any]) -> dict[str, Any]:
    line = payload.get("line")
    if isinstance(line, dict):
        return line
    return {
        "description": payload.get("item") or payload.get("description") or "",
        "quantity": payload.get("qty") or payload.get("quantity"),
        "unit_price": payload.get("unit_price"),
        "vat_percent": payload.get("vat_percent") or payload.get("vat_pct"),
    }


def _coerce_totals(payload: dict[str, Any]) -> dict[str, Any]:
    totals = payload.get("totals")
    if isinstance(totals, dict):
        return totals
    return {
        "subtotal_ex_vat": payload.get("subtotal_ex_vat") or payload.get("subtotal"),
        "vat_amount": payload.get("vat_amount"),
        "total_inc_vat": payload.get("total_inc_vat") or payload.get("total"),
        "vat_percent": payload.get("vat_percent") or payload.get("vat_pct"),
    }


def render_receipt_pdf(output_path: str, payload: dict, company: dict) -> bytes:
    """Render a minimal receipt/invoice PDF and return its bytes."""
    payload = payload or {}
    company = _coerce_company(company)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    title = "Receipt / Invoice"
    company_name = company.get("name") or "N/A"
    invoice_no = (
        payload.get("invoice_no")
        or payload.get("receipt_no")
        or payload.get("invoice_number")
        or "N/A"
    )
    customer = _coerce_customer(payload)
    line = _coerce_line(payload)
    totals = _coerce_totals(payload)
    currency = payload.get("currency") or "EUR"
    reference = payload.get("reference") or payload.get("notes") or "N/A"
    payment_method = payload.get("payment_method") or payload.get("pay_method") or "N/A"

    y = height - 72
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, title)
    y -= 36

    c.setFont("Helvetica", 12)
    c.drawString(72, y, f"Company: {company_name}")
    y -= 18
    if company.get("id"):
        c.drawString(72, y, f"Company ID: {_format_value(company.get('id'))}")
        y -= 18
    if company.get("vat"):
        c.drawString(72, y, f"Company VAT: {_format_value(company.get('vat'))}")
        y -= 18
    if company.get("address"):
        c.drawString(72, y, f"Company address: {_format_value(company.get('address'))}")
        y -= 18
    if company.get("email"):
        c.drawString(72, y, f"Company email: {_format_value(company.get('email'))}")
        y -= 18
    if company.get("phone"):
        c.drawString(72, y, f"Company phone: {_format_value(company.get('phone'))}")
        y -= 18
    if company.get("web"):
        c.drawString(72, y, f"Company web: {_format_value(company.get('web'))}")
        y -= 18
    c.drawString(72, y, f"Invoice #: {invoice_no}")
    y -= 18
    c.drawString(72, y, f"Issue date: {_format_date(payload.get('issue_date') or payload.get('date'))}")
    y -= 18
    c.drawString(72, y, f"Due date: {_format_date(payload.get('due_date'))}")
    y -= 18
    c.drawString(72, y, f"Customer: {_format_value(customer.get('name'))}")
    customer_address = customer.get("address") or ""
    if customer_address:
        y -= 18
        c.drawString(72, y, f"Customer address: {_format_value(customer_address)}")
    customer_email = customer.get("email") or ""
    if customer_email:
        y -= 18
        c.drawString(72, y, f"Customer email: {_format_value(customer_email)}")
    customer_vat = customer.get("vat_id") or ""
    if customer_vat:
        y -= 18
        c.drawString(72, y, f"Customer VAT ID: {_format_value(customer_vat)}")
    y -= 18
    c.drawString(72, y, f"Reference: {_format_value(reference)}")
    y -= 18
    c.drawString(72, y, f"Payment method: {_format_value(payment_method)}")
    y -= 18
    c.drawString(72, y, f"Item: {_format_value(line.get('description'))}")
    y -= 18
    c.drawString(72, y, f"Quantity: {_format_value(line.get('quantity'))}")
    y -= 18
    c.drawString(72, y, f"Unit price: {_format_amount(line.get('unit_price'))} {currency}")
    y -= 18
    vat_percent = _format_amount(line.get("vat_percent"))
    vat_rate_text = f"{vat_percent}%" if vat_percent != "N/A" else "N/A"
    c.drawString(72, y, f"VAT rate: {vat_rate_text}")
    y -= 18
    c.drawString(72, y, f"Subtotal: {_format_amount(totals.get('subtotal_ex_vat'))} {currency}")
    y -= 18
    c.drawString(72, y, f"VAT: {_format_amount(totals.get('vat_amount'))} {currency}")
    y -= 18
    c.drawString(72, y, f"Total: {_format_amount(totals.get('total_inc_vat'))} {currency}")

    c.showPage()
    c.save()

    return path.read_bytes()
