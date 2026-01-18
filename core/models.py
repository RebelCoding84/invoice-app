from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Customer:
    """Invoice customer details."""

    name: str
    email: str = ""
    address: str = ""
    vat_id: str = ""


@dataclass
class InvoiceLine:
    """Single invoice line for MVP."""

    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_percent: Decimal


@dataclass
class InvoiceDraft:
    """Input data required to create an invoice."""

    customer: Customer
    line: InvoiceLine
    payment_method: str
    notes: str
    currency: str = "EUR"
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


@dataclass
class InvoiceOptions:
    """Optional processing features."""

    generate_finvoice: bool
    enable_backup: bool


@dataclass
class InvoiceArtifacts:
    """Binary artifacts created by invoice processing."""

    pdf_bytes: bytes
    finvoice_bytes: Optional[bytes]
    invoice_no: str


@dataclass
class InvoiceResult:
    """Output from invoice processing."""

    totals: dict
    artifacts: InvoiceArtifacts
    paths: dict
