from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook


HEADERS = [
    "timestamp",
    "invoice_no",
    "customer_name",
    "subtotal_ex_vat",
    "vat_amount",
    "total_inc_vat",
    "currency",
]


def _ensure_headers(ws) -> None:
    if ws.max_row < 1:
        ws.append(HEADERS)
        return
    row = [cell.value for cell in ws[1]]
    if any(row) and row[: len(HEADERS)] == HEADERS:
        return
    if not any(row):
        ws.append(HEADERS)


def write_ledger_xlsx(path: str, row: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        workbook = load_workbook(target)
        sheet = workbook.active
        _ensure_headers(sheet)
    else:
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(HEADERS)

    sheet.append([row.get(header) for header in HEADERS])
    workbook.save(target)
