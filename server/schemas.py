from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from core.models import InvoiceStatus


class CustomerPayload(BaseModel):
    name: str
    email: str = ""
    address: str = ""
    vat_id: str = ""


class InvoiceLinePayload(BaseModel):
    description: str
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    vat_percent: Decimal = Field(ge=0)


class InvoiceOptionsPayload(BaseModel):
    generate_finvoice: bool = False
    enable_backup: bool = True


class InvoiceCreateRequest(BaseModel):
    customer: CustomerPayload
    line: InvoiceLinePayload
    payment_method: str = ""
    notes: str = ""
    currency: str = "EUR"
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    options: InvoiceOptionsPayload = Field(default_factory=InvoiceOptionsPayload)


class InvoiceCreateResponse(BaseModel):
    invoice_no: str
    totals: dict
    has_finvoice: bool


class InvoiceLifecycleResponse(BaseModel):
    invoice_no: str
    event_type: str
    status: InvoiceStatus
    status_changed_at: datetime
    created_at: Optional[datetime] = None


class InvoiceTotalsResponse(BaseModel):
    invoice_no: str
    subtotal: str
    vat: str
    total: str
    currency: str
