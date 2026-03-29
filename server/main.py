from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import core.invoice_service as invoice_service
from core.invoice_service import create_invoice
from core.models import Customer, InvoiceDraft, InvoiceLine, InvoiceOptions
from server.schemas import (
    InvoiceCreateRequest,
    InvoiceCreateResponse,
    InvoiceLifecycleResponse,
    InvoiceTotalsResponse,
)
from server.security import verify_api_key
from server.settings import API_HOST, API_PORT
from storage.excel import read_invoice_totals
from storage.ledger import read_invoice_lifecycle_metadata

app = FastAPI(title="Rebel Invoice API", version="0.2.x")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)


def _find_file(base: Path, pattern: str) -> Path | None:
    matches = list(base.rglob(pattern))
    return matches[0] if matches else None


def _invoice_pattern(invoice_no: str, prefix: str, ext: str) -> str:
    if invoice_no.isdigit():
        invoice_no = f"{int(invoice_no):06d}"
    return f"{prefix}_{invoice_no}.{ext}"


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/api/v1/invoices",
    response_model=InvoiceCreateResponse,
    dependencies=[Depends(verify_api_key)],
)
def create_invoice_endpoint(payload: InvoiceCreateRequest) -> InvoiceCreateResponse:
    draft = InvoiceDraft(
        customer=Customer(**payload.customer.model_dump()),
        line=InvoiceLine(**payload.line.model_dump()),
        payment_method=payload.payment_method,
        notes=payload.notes,
        currency=payload.currency,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
    )
    options = InvoiceOptions(**payload.options.model_dump())
    try:
        result = create_invoice(draft, options)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    totals = {k: str(v) for k, v in result.totals.items()}
    return InvoiceCreateResponse(
        invoice_no=result.artifacts.invoice_no,
        totals=totals,
        has_finvoice=bool(result.artifacts.finvoice_bytes),
    )


@app.get(
    "/api/v1/invoices/{invoice_no}/lifecycle",
    response_model=InvoiceLifecycleResponse,
    dependencies=[Depends(verify_api_key)],
)
def get_invoice_lifecycle(invoice_no: str) -> InvoiceLifecycleResponse:
    metadata = read_invoice_lifecycle_metadata(invoice_no)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Invoice lifecycle not found")
    return InvoiceLifecycleResponse(**metadata)


@app.get(
    "/api/v1/invoices/{invoice_no}/totals",
    response_model=InvoiceTotalsResponse,
    dependencies=[Depends(verify_api_key)],
)
def get_invoice_totals(invoice_no: str) -> InvoiceTotalsResponse:
    totals = read_invoice_totals(invoice_service.DATA_DIR / "ledger.xlsx", invoice_no)
    if totals is None:
        raise HTTPException(status_code=404, detail="Invoice totals not found")
    return InvoiceTotalsResponse(**totals)


@app.get(
    "/api/v1/invoices/{invoice_no}/pdf",
    dependencies=[Depends(verify_api_key)],
)
def get_invoice_pdf(invoice_no: str) -> FileResponse:
    pattern = _invoice_pattern(invoice_no, "receipt", "pdf")
    path = _find_file(Path("storage"), f"**/receipts/{pattern}")
    if not path:
        legacy_pattern = pattern.replace(".pdf", "_tmp.pdf")
        path = _find_file(Path("storage"), f"**/receipts/{legacy_pattern}")
    if not path:
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@app.get(
    "/api/v1/invoices/{invoice_no}/finvoice",
    dependencies=[Depends(verify_api_key)],
)
def get_invoice_finvoice(invoice_no: str) -> FileResponse:
    pattern = _invoice_pattern(invoice_no, "finvoice", "xml")
    path = _find_file(Path("storage"), f"**/exports/{pattern}")
    if not path:
        raise HTTPException(status_code=404, detail="Finvoice XML not found")
    return FileResponse(path, media_type="application/xml", filename=path.name)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=API_HOST, port=API_PORT)
