# User Guide

## Lite UI

1. Install dependencies:
   ```bash
   pixi install
   ```
2. Start the Lite UI:
   ```bash
   pixi run lite
   ```
3. Open `http://127.0.0.1:8501` in your browser.
4. Fill in the customer, line, payment method, and notes fields.
5. Submit the form to create the invoice and download the PDF. Enable Finvoice if you also want the XML export.

## API

1. Start the API:
   ```bash
   pixi run api
   ```
2. The base URL is `http://127.0.0.1:8000`.
3. Send `X-API-Key: dev-key` unless you have overridden `API_KEY` locally.
4. Create invoices with `POST /api/v1/invoices`.
5. Download artifacts with:
   - `GET /api/v1/invoices/{invoice_no}/pdf`
   - `GET /api/v1/invoices/{invoice_no}/finvoice`

## Pro UI

1. Change into the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Make sure the API is running locally.
4. If needed, set `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` and `NEXT_PUBLIC_API_KEY=dev-key`.
5. Start the Pro UI:
   ```bash
   npm run dev
   ```
6. Open `http://127.0.0.1:3000`.

## Typical Flow

- Create an invoice in Lite UI or Pro UI.
- Review the returned invoice number and totals.
- Download the PDF and optional Finvoice XML from the app or through the API download endpoints.
- If validation errors appear, fix the input or local configuration and submit again.
