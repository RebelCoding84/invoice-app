# Rebel Invoice API (Local)

API key auth is required via `X-API-Key`.

## Create invoice
```bash
curl -X POST http://127.0.0.1:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key" \
  -d '{
    "customer": {"name": "Test Customer", "email": "", "address": "", "vat_id": ""},
    "line": {"description": "Service", "quantity": "1", "unit_price": "100.00", "vat_percent": "24.00"},
    "payment_method": "Bank transfer",
    "notes": "Thanks",
    "currency": "EUR",
    "options": {"generate_finvoice": true, "enable_backup": true}
  }'
```

## Download PDF
```bash
curl -o receipt.pdf \
  -H "X-API-Key: dev-key" \
  http://127.0.0.1:8000/api/v1/invoices/000001/pdf
```

## Download Finvoice XML
```bash
curl -o finvoice.xml \
  -H "X-API-Key: dev-key" \
  http://127.0.0.1:8000/api/v1/invoices/000001/finvoice
```
