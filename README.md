Huom: UI tukee suomea ja englantia (fi/en).

# Invoice App (Lite UI + API + Pro UI)

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

## Modes
- Lite: Streamlit UI for local operation
- API: FastAPI wrapper around core service
- Pro: Next.js dashboard and invoice creation UI

## Project Structure
```
invoice-app/
  app.py
  config.py
  core/
    invoice_service.py
    models.py
  requirements.txt
  server/
    main.py
    schemas.py
    security.py
    settings.py
  frontend/
    README.md
    src/app/
  run.bat
  README.md
  locales/
    fi.json
    en.json
  outputs/
    pdf.py
    finvoice.py
  storage/
    archive_manager.py
    backup_manager.py
    excel.py
    ledger.py
  utils/
    atomic.py
    i18n.py
    sanitization.py
    money.py
```

## Quick Start (Windows PowerShell)

### 1) Lite UI (Streamlit)
```powershell
cd C:\Projektit\invoice-app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m streamlit run app.py --server.port 8501 --server.fileWatcherType poll
```
Runs on http://127.0.0.1:8501

### 2) API (FastAPI)
```powershell
cd C:\Projektit\invoice-app
.\.venv\Scripts\Activate.ps1
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```
Test: http://127.0.0.1:8000/api/v1/health  
Docs: http://127.0.0.1:8000/docs

### 3) Pro UI (Next.js)
```powershell
cd C:\Projektit\invoice-app\frontend
npm.cmd install
npm.cmd run dev
```
Runs on http://127.0.0.1:3000  
Note: the backend API must be running at the same time.
API base URL: http://127.0.0.1:8000

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
- `data/`: sequence counter and Excel ledger
- `storage/YYYY/MM/`: monthly archive for receipts, exports, and metadata
- `storage/**/meta/ledger_YYYY-MM.jsonl`: append-only integrity ledger
- `backups/`: ZIP backups of monthly folders

## Security Notes
- Local-first: no cloud dependency by default
- Append-only JSONL ledger for traceability
- SHA-256 hashes for PDF integrity checks

## Troubleshooting
- PowerShell ExecutionPolicy blocks npm: use `npm.cmd`
- Missing Python deps: run `pip install -r requirements.txt`
- PowerShell blocks Activate.ps1: run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again

## Roadmap
- Improved invoice layout and styling
- Company logo support
- IBAN, payment terms, and references
- Export formats (CSV/XML)
- Document signing and verification

## License
Planned: AGPLv3. (Placeholder)
