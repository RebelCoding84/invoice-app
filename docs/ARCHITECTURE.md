# Architecture

Invoice App is organized around one shared core path for invoice creation, PDF generation, and Finvoice generation.

## Layers

- Lite UI: Streamlit app in `app.py` for local-first manual entry.
- Pro UI: Next.js app in `frontend/` for browser-based entry.
- API: FastAPI app in `server/main.py` for the Pro UI and other local integrations.
- Core service: `core/invoice_service.py` creates invoices, allocates invoice numbers, validates critical input, and builds document payloads.
- Outputs: `outputs/pdf.py` renders PDF files and `outputs/finvoice.py` renders Finvoice XML.
- Storage: `data/`, `storage/YYYY/MM/`, and `backups/` hold sequence data, generated artifacts, and backups.

## Shared-Path Principle

- Both Lite and Pro should collect user input and then call the shared core service.
- Business rules should stay in core, not duplicated in the UI.
- The core service is the source of truth for totals, numbering, document payloads, and persistence.
- PDF and Finvoice should consume canonical data from the core path.

## Document Flow

- Lite UI builds a `Customer`, `InvoiceLine`, `InvoiceDraft`, and `InvoiceOptions`, then calls `create_invoice(...)`.
- Pro UI sends the same logical input through the API, which converts request models into the same core dataclasses.
- Core builds the invoice payload, writes the PDF and optional Finvoice XML, and appends ledger entries.
- API download routes read the generated files from local storage.
