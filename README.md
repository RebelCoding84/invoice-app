# Invoice App

Local-first invoice and receipt application designed for small businesses and independent professionals.  
The system focuses on reliability, auditability, and simplicity, without mandatory cloud dependencies.

The application provides a Streamlit-based user interface for creating invoices and receipts, generating PDF documents and Finvoice XML files, and maintaining a verifiable local transaction ledger.

---

## Overview

Invoice App is built around a clear separation of concerns:

- **User Interface**: Streamlit-based Lite UI for local operation
- **Core logic**: Centralized invoice calculation and document generation
- **Storage**: Append-only ledger and monthly archive structure
- **Extensibility**: Optional API and browser-based Pro UI for future expansion

The system is intentionally local-first and deterministic, making it suitable for environments where data sovereignty and transparency are required.

---

## Key Features

- Streamlit UI with Finnish and English language support (fi/en)
- PDF invoice and receipt generation (ReportLab)
- Finvoice XML generation for manual bank/operator upload
- Centralized monetary calculations using Decimal arithmetic
- Append-only JSONL integrity ledger with SHA-256 hash chaining
- Monthly storage structure (`storage/YYYY/MM`)
- Optional ZIP backups with retention policy
- Atomic file writes (Windows-safe)
- No mandatory external services or cloud dependencies

---

## Architecture Modes

The application supports multiple execution modes:

### Lite UI (Primary Mode)
- Streamlit-based local user interface
- Intended for direct user interaction and document generation
- Fully functional without API or browser-based UI

### API (Extension)
- FastAPI wrapper around the core service
- Enables programmatic access and integration
- Used by the Pro UI

### Pro UI (Extension)
- Next.js-based browser interface
- Provides a dashboard-style experience
- Requires the API to be running

Only the Lite UI is required for core functionality.

---

## Quick Start

### Prerequisites

- Pixi (deterministic Python environment manager)

### Install and Run (Lite UI)

```bash
pixi install
pixi run smoke
pixi run lite
```

The Streamlit interface will open in your browser.
From the UI, you can create invoices or receipts and export PDF and Finvoice XML files.

---

## Project Structure (High Level)

```
invoice-app/
  app.py
  config.py
  core/
  server/
  frontend/
  outputs/
  storage/
  utils/
  locales/
  scripts/
```

---

## Data and Storage

`data/`  
Stores sequence counters and ledger-related metadata.

`storage/YYYY/MM/`  
Monthly archive containing generated documents and metadata.

`storage/**/meta/*.jsonl`  
Append-only integrity ledger with SHA-256 hash chaining.

`backups/`  
Optional ZIP backups of monthly archives.

---

## Security and Integrity

- Local-first design (no cloud dependency by default)
- Append-only ledger for traceability
- SHA-256 hashing for document integrity
- Atomic file operations to prevent partial writes

---

## Configuration

Configuration is handled via environment variables.

Common variables include:

- `TIMEZONE` (default: `Europe/Helsinki`)
- `BACKUP_ENABLED` (default: `true`)
- `BACKUP_RETENTION_DAYS`
- `DEFAULT_LOCALE` (`fi` / `en`)
- `DEFAULT_PROVIDER`
- `COMPANY_NAME`
- `COMPANY_ID`
- `COMPANY_VAT`
- `COMPANY_ADDRESS`
- `COMPANY_EMAIL`
- `COMPANY_PHONE`
- `COMPANY_WEB`

An example configuration file can be provided separately if needed.

---

## Known Limitations

- PDF invoice number rendering may be incomplete in the current version, even when the Finvoice XML contains a valid invoice number.
- Finvoice XML generation currently targets manual bank/operator upload workflows.
- Automated sending and operator-level validation are planned for future versions.

---

## Roadmap

- Improved PDF layout and styling
- Company logo support
- Full payment terms and reference handling
- Enhanced Finvoice compliance validation
- Automated bank/operator submission workflows
- Digital signing and verification

---

## License

Planned: AGPLv3  
(Currently a placeholder until the licensing model is finalized.)
