# Privacy

Invoice App is local-first. It processes business data on the machine running the app and does not require a cloud service for core document generation.

## Data Processed

- Customer data: name, email, address, VAT ID
- Invoice data: line description, quantity, unit price, VAT percent, payment method, notes, currency, dates
- Company data: values loaded from environment variables
- Generated artifacts: PDF, Finvoice XML, ledger metadata, hashes, and timestamps

## Storage

- `data/` stores sequence and ledger-related files.
- `storage/YYYY/MM/` stores generated documents and metadata.
- `backups/` stores optional ZIP backups.

## Privacy Principles

- Collect only the data needed to create and audit the document.
- Keep generated files and audit data local by default.
- Avoid adding extra personal data fields unless they are required for the document workflow.
- Do not introduce external transmission of invoice data unless the repository explicitly adds that feature later.
