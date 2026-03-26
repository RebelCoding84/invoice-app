from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO
from xml.etree import ElementTree as ET

from core.models import InvoiceDraft


def _to_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return datetime.now()


def _text(parent: ET.Element, tag: str, value) -> ET.Element:
    elem = ET.SubElement(parent, tag)
    if value is not None:
        elem.text = str(value)
    return elem


def _coerce_seller(seller: dict) -> dict[str, str]:
    seller = seller or {}
    return {
        "name": seller.get("name") or seller.get("company_name") or seller.get("COMPANY_NAME") or "",
        "id": seller.get("id") or seller.get("company_id") or seller.get("COMPANY_ID") or "",
        "vat": seller.get("vat") or seller.get("company_vat") or seller.get("COMPANY_VAT") or "",
        "address": seller.get("address") or seller.get("company_address") or seller.get("COMPANY_ADDRESS") or "",
        "email": seller.get("email") or seller.get("company_email") or seller.get("COMPANY_EMAIL") or "",
        "phone": seller.get("phone") or seller.get("company_phone") or seller.get("COMPANY_PHONE") or "",
        "web": seller.get("web") or seller.get("company_web") or seller.get("COMPANY_WEB") or "",
    }


def generate_finvoice_minimal_xml(
    draft: InvoiceDraft, totals: dict, seller: dict
) -> bytes:
    """Generate a minimal Finvoice XML payload as UTF-8 bytes."""
    issue_date = draft.issue_date or datetime.now()
    due_date = draft.due_date or issue_date + timedelta(days=14)
    created_dt = _to_datetime(issue_date)
    due_dt = _to_datetime(due_date)

    seller = _coerce_seller(seller)
    invoice_no = totals.get("invoice_no") or totals.get("receipt_no") or ""
    currency = draft.currency or "EUR"

    root = ET.Element("Finvoice", Version="3.0")

    _text(root, "InvoiceNumber", invoice_no)
    _text(root, "InvoiceDate", created_dt.date().isoformat())
    _text(root, "InvoiceDueDate", due_dt.date().isoformat())
    _text(root, "InvoiceCurrencyCode", currency)

    seller_details = ET.SubElement(root, "SellerPartyDetails")
    _text(seller_details, "SellerPartyName", seller.get("name") or "")
    _text(seller_details, "SellerPartyIdentifier", seller.get("id") or "")

    buyer_details = ET.SubElement(root, "BuyerPartyDetails")
    _text(buyer_details, "BuyerPartyName", draft.customer.name)
    _text(buyer_details, "BuyerPartyStreetName", draft.customer.address)

    row = ET.SubElement(root, "InvoiceRow")
    _text(row, "ArticleName", draft.line.description)
    _text(row, "InvoicedQuantity", draft.line.quantity)
    _text(row, "UnitPriceAmount", draft.line.unit_price)
    _text(row, "RowAmount", totals.get("subtotal_ex_vat"))
    _text(row, "RowVatRatePercent", totals.get("vat_percent"))
    _text(row, "RowVatAmount", totals.get("vat_amount"))
    _text(row, "RowAmountVatIncluded", totals.get("total_inc_vat"))

    totals_elem = ET.SubElement(root, "InvoiceTotals")
    _text(totals_elem, "VatExclusiveAmount", totals.get("subtotal_ex_vat"))
    _text(totals_elem, "VatAmount", totals.get("vat_amount"))
    _text(totals_elem, "VatInclusiveAmount", totals.get("total_inc_vat"))

    tree = ET.ElementTree(root)
    buffer = BytesIO()
    tree.write(buffer, encoding="utf-8", xml_declaration=True)
    return buffer.getvalue()


def validate_finvoice_bytes(xml_bytes: bytes) -> bool:
    """Validate that Finvoice XML has root and totals fields."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return False
    if root.tag != "Finvoice":
        return False
    totals = root.find("InvoiceTotals")
    if totals is None:
        return False
    required = ["VatExclusiveAmount", "VatAmount", "VatInclusiveAmount"]
    for tag in required:
        elem = totals.find(tag)
        if elem is None or elem.text is None:
            return False
    return True
