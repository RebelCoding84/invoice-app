from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from config import (
    BACKUP_ENABLED,
    COMPANY_ADDRESS,
    COMPANY_EMAIL,
    COMPANY_ID,
    COMPANY_NAME,
    COMPANY_PHONE,
    COMPANY_VAT,
    COMPANY_WEB,
    DATA_DIR,
    DEFAULT_LOCALE,
    DEFAULT_PROVIDER,
    LOG_DIR,
    TIMEZONE,
)
from outputs.pdf import render_receipt_pdf
from storage import excel, ledger
from storage.archive_manager import move_receipt_to_month
from storage.backup_manager import create_backup_zip
from utils.atomic import atomic_write_text
from utils.i18n import load_locale, t


def _setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("invoice_app")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def _get_now() -> datetime:
    try:
        tz = ZoneInfo(TIMEZONE)
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz=tz)


def _next_receipt_no(seq_path: Path) -> int:
    seq_path.parent.mkdir(parents=True, exist_ok=True)
    current = 0
    if seq_path.exists():
        try:
            current = int(seq_path.read_text(encoding="utf-8").strip() or 0)
        except ValueError:
            current = 0
    new_value = current + 1
    atomic_write_text(str(seq_path), f"{new_value}\n", encoding="utf-8")
    return new_value


st.set_page_config(page_title="Rebel Invoice", layout="wide")
logger = _setup_logging()

st.title("Rebel Invoice - MVP")

lang_options = ["fi", "en"]
default_lang = DEFAULT_LOCALE if DEFAULT_LOCALE in lang_options else "fi"
lang_code = st.sidebar.selectbox(
    "Language",
    lang_options,
    index=lang_options.index(default_lang),
)
provider = st.sidebar.selectbox("Provider", ["local"], index=0)
show_settings = st.sidebar.checkbox("Show settings", value=False)

lang = load_locale(lang_code)

if show_settings:
    st.sidebar.write(f"DEFAULT_PROVIDER: {DEFAULT_PROVIDER}")
    st.sidebar.write(f"DATA_DIR: {DATA_DIR}")
    st.sidebar.write(f"LOG_DIR: {LOG_DIR}")
    st.sidebar.write(f"TIMEZONE: {TIMEZONE}")
    st.sidebar.write(f"BACKUP_ENABLED: {BACKUP_ENABLED}")

with st.form("receipt_form"):
    customer = st.text_input(t("customer", lang))
    item_name = st.text_input(t("item", lang))
    qty = st.number_input(t("qty", lang), min_value=0.0, step=1.0, value=1.0)
    unit_price = st.number_input(t("unit_price", lang), min_value=0.0, step=0.01, value=0.0)
    vat_pct = st.number_input(t("vat_pct", lang), min_value=0.0, step=0.1, value=24.0)
    pay_method = st.text_input(t("pay_method", lang))
    note = st.text_area(t("note", lang))
    submitted = st.form_submit_button(t("save", lang))

subtotal = qty * unit_price
vat_amount = subtotal * (vat_pct / 100.0)
total = subtotal + vat_amount

st.subheader(t("preview", lang))
st.write(f"Subtotal: {subtotal:.2f} EUR")
st.write(f"VAT: {vat_amount:.2f} EUR")
st.write(f"Total: {total:.2f} EUR")

if submitted:
    now = _get_now()
    receipt_no = _next_receipt_no(DATA_DIR / "sequence.txt")
    created_at = now.isoformat()

    payload = {
        "receipt_no": receipt_no,
        "date": created_at,
        "customer_name": customer,
        "reference": note,
        "total": f"{total:.2f}",
        "currency": "EUR",
        "items": [
            {
                "name": item_name,
                "qty": qty,
                "price": f"{unit_price:.2f} EUR",
            }
        ],
    }
    company = {
        "name": COMPANY_NAME,
        "address": COMPANY_ADDRESS,
        "id": COMPANY_ID,
        "vat": COMPANY_VAT,
        "email": COMPANY_EMAIL,
        "phone": COMPANY_PHONE,
        "web": COMPANY_WEB,
    }

    try:
        tmp_dir = Path("outputs")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        temp_pdf_path = tmp_dir / f"receipt_{receipt_no:06d}_tmp.pdf"
        render_receipt_pdf(str(temp_pdf_path), payload, company)
        final_pdf_path = move_receipt_to_month(str(temp_pdf_path), now, receipt_no)
        excel_row = excel.save_row_to_excel(
            str(DATA_DIR / "ledger.xlsx"),
            {
                "receipt_no": receipt_no,
                "created_at": created_at,
                "customer": customer,
                "item": item_name,
                "qty": qty,
                "unit_price": unit_price,
                "vat_pct": vat_pct,
                "subtotal": subtotal,
                "vat": vat_amount,
                "total": total,
                "pay_method": pay_method,
                "note": note,
                "provider": provider,
                "pdf_path": final_pdf_path,
            },
        )
        pdf_sha256 = ledger.compute_sha256(final_pdf_path)
        ledger.append_event(
            now,
            {
                "event_type": "SUCCESS",
                "receipt_no": receipt_no,
                "pdf_path": final_pdf_path,
                "pdf_sha256": pdf_sha256,
                "excel_row": excel_row,
                "created_at": created_at,
            },
        )
        if BACKUP_ENABLED:
            create_backup_zip(now)

        st.success(t("saved", lang))
        with open(final_pdf_path, "rb") as handle:
            st.download_button(
                t("download_pdf", lang),
                data=handle.read(),
                file_name=Path(final_pdf_path).name,
                mime="application/pdf",
            )
        logger.info("Saved receipt %s", receipt_no)
    except Exception as exc:
        try:
            ledger.append_event(
                now,
                {
                    "event_type": "FAILED",
                    "receipt_no": receipt_no,
                    "reason": str(exc),
                    "created_at": created_at,
                },
            )
        except Exception:
            logger.exception("Failed to append FAILED ledger event")
        logger.exception("Receipt save failed")
        st.error(str(exc))
