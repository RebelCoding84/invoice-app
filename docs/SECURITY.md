# Security

Invoice App is designed for local-first operation. The default workflow keeps invoice data, generated documents, and audit data on the local machine.

## Current Security Posture

- The API is protected by `X-API-Key`.
- Company and runtime settings are loaded from environment variables.
- Input is validated in the UI, API, and core service before documents are generated.
- CORS is limited to local development origins for the Pro UI connection.

## Rules

- Do not hardcode secrets, tokens, passwords, or company-specific sensitive values.
- Do not weaken validation or auditability for convenience.
- Do not add network dependencies to the core invoice flow.
- Keep file paths and storage behavior explicit and local.

## Before Merge

- Run the test suite for the affected area.
- Verify invoice numbering, totals, and document generation behavior.
- Check that validation failures surface as client errors where expected.
- Review any change touching `COMPANY_*` settings, file paths, or ledger writes carefully.
