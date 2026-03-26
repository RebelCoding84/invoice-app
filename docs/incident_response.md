# Incident Response

Use this guide when invoice creation, PDF generation, or Finvoice generation fails.

## First Checks

- Read the UI error message or API response detail.
- Check `logs/app.log` for Lite UI failures.
- Check the API console output for FastAPI errors.
- Confirm `GET /api/v1/health` returns `{"status":"ok"}`.
- Verify local config values such as `COMPANY_NAME`, `COMPANY_ID`, `API_KEY`, `DATA_DIR`, and `BACKUP_DIR`.

## If Invoice Creation Fails

- Fix the reported validation error and retry.
- Validation errors are client-side issues and should be corrected in input or configuration.
- Do not edit ledger files manually unless you are performing a controlled recovery.

## If PDF Generation Fails

- Confirm the invoice was created and an `invoice_no` was returned.
- Check the local PDF path under `storage/YYYY/MM/receipts/`.
- Use `GET /api/v1/invoices/{invoice_no}/pdf` to confirm the file can be downloaded.

## If Finvoice Generation Fails

- Confirm `generate_finvoice` was enabled.
- Confirm `COMPANY_ID` is set.
- Check the export path under `storage/YYYY/MM/exports/`.
- Use `GET /api/v1/invoices/{invoice_no}/finvoice` to verify the XML exists.

## Recovery Steps

- Correct the missing or invalid input/configuration.
- Restart Lite UI, API, or Pro UI if the process is stale.
- Re-run invoice creation after fixing the issue.
- If the app still fails, capture the exact error text and the relevant log lines before making further changes.
