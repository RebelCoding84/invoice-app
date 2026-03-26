# API

Local FastAPI base URL: `http://127.0.0.1:8000`

## Authentication

- Send `X-API-Key` with every protected request.
- Default local development key: `dev-key`.
- Missing or invalid keys return `401 Unauthorized`.

## Health

- `GET /api/v1/health`
- Returns `{"status":"ok"}`

## Create Invoice

- `POST /api/v1/invoices`
- Required body sections:
  - `customer`
  - `line`
  - `options`
- Common fields:
  - `payment_method`
  - `notes`
  - `currency`
  - `issue_date`
  - `due_date`

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key" \
  -d '{
    "customer": {
      "name": "Test Customer",
      "email": "",
      "address": "",
      "vat_id": ""
    },
    "line": {
      "description": "Service",
      "quantity": "1",
      "unit_price": "100.00",
      "vat_percent": "24.00"
    },
    "payment_method": "Bank transfer",
    "notes": "Thanks",
    "currency": "EUR",
    "options": {
      "generate_finvoice": true,
      "enable_backup": true
    }
  }'
```

Success response includes:

- `invoice_no`
- `totals`
- `has_finvoice`

Validation behavior:

- Expected invoice creation validation failures return `422 Unprocessable Entity`.
- The response `detail` contains the validation message from the core service.
- Unexpected failures still surface as `500` errors.

## Download Generated Files

- `GET /api/v1/invoices/{invoice_no}/pdf`
- `GET /api/v1/invoices/{invoice_no}/finvoice`

Example:

```bash
curl -o receipt.pdf \
  -H "X-API-Key: dev-key" \
  http://127.0.0.1:8000/api/v1/invoices/000001/pdf

curl -o finvoice.xml \
  -H "X-API-Key: dev-key" \
  http://127.0.0.1:8000/api/v1/invoices/000001/finvoice
```
