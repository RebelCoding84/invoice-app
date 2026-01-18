Huom: UI tukee suomea ja englantia (fi/en).

# Invoice App (Streamlit MVP)

## Overview
Local-first Streamlit app for creating simple receipts/invoices for small businesses. It generates PDFs, logs events in an append-only ledger, and keeps data in a monthly storage structure without any cloud requirement.

## Features
- Streamlit UI with fi/en locale support
- PDF receipt generation via ReportLab
- Excel ledger (`ledger.xlsx`) via openpyxl
- Append-only JSONL integrity ledger with SHA-256 hashes
- Monthly archive folders (`storage/YYYY/MM`)
- Atomic writes safe for Windows
- Optional ZIP backups with retention
- Local-only operation (no external services required)

## Project Structure
```
invoice-app/
  app.py
  config.py
  requirements.txt
  run.bat
  README.md
  locales/
    fi.json
    en.json
  outputs/
    pdf.py
  storage/
    archive_manager.py
    backup_manager.py
    excel.py
    ledger.py
  utils/
    atomic.py
    i18n.py
    sanitization.py
```

## Quick Start (Windows PowerShell)
```powershell
cd C:\Projektit\invoice-app
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## API Server (FastAPI)
Start the local API wrapper around the core service:
```powershell
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

## Configuration (.env)
Key environment variables:
- `TIMEZONE` (default: `Europe/Helsinki`)
- `BACKUP_ENABLED` (default: `true`)
- `BACKUP_RETENTION_DAYS` (default: `30`)
- `DEFAULT_LOCALE` (default: `fi`)
- `DEFAULT_PROVIDER` (default: `rebel`)
- `COMPANY_NAME`, `COMPANY_ID`, `COMPANY_VAT`
- `COMPANY_ADDRESS`, `COMPANY_EMAIL`, `COMPANY_PHONE`, `COMPANY_WEB`

## Data & Storage
- `data/sequence.txt`: receipt number sequence
- `data/ledger.xlsx`: Excel log of receipts
- `storage/YYYY/MM/`: monthly archive
  - `receipts/` for PDFs
  - `meta/ledger_YYYY-MM.jsonl` append-only integrity ledger
- `backups/`: ZIP backups of monthly folders

## Security Notes
- Local-first: no cloud dependency by default
- Append-only JSONL ledger for traceability
- SHA-256 hashes for PDF integrity checks

## Roadmap
- Improved invoice layout and styling
- Company logo support
- IBAN, payment terms, and references
- Export formats (CSV/XML)
- Document signing and verification

## License
Planned: AGPLv3. (Placeholder)
