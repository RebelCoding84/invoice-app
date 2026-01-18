from __future__ import annotations

import logging
from decimal import Decimal
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
from outputs.finvoice import generate_finvoice_xml
from outputs.pdf import render_receipt_pdf
from storage import catalog, excel, ledger
from storage.archive_manager import move_receipt_to_month
from storage.backup_manager import create_backup_zip
from utils.atomic import atomic_write_text
from utils.i18n import load_locale, t
from utils.money import calculate_totals


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

customers = catalog.load_customers(DATA_DIR)
customer_names = [c.get("name", "").strip() for c in customers if c.get("name")]
customer_options = customer_names + ["(new)"]
default_customer = customer_names[0] if customer_names else "(new)"
customer_choice = st.sidebar.selectbox(
    "Customer",
    customer_options,
    index=customer_options.index(default_customer),
    key="customer_select",
)

if customer_choice != "(new)":
    if st.session_state.get("_customer_selected") != customer_choice:
        st.session_state["customer_name_input"] = customer_choice
        st.session_state["_customer_selected"] = customer_choice
else:
    new_customer_name = st.sidebar.text_input("Name", key="new_customer_name")
    new_customer_email = st.sidebar.text_input("Email", key="new_customer_email")
    new_customer_address = st.sidebar.text_input("Address", key="new_customer_address")
    new_customer_vat = st.sidebar.text_input("VAT ID", key="new_customer_vat")
    if st.sidebar.button("Save customer"):
        if new_customer_name.strip():
            catalog.upsert_customer(
                DATA_DIR,
                {
                    "name": new_customer_name.strip(),
                    "email": new_customer_email.strip(),
                    "address": new_customer_address.strip(),
                    "vat_id": new_customer_vat.strip(),
                },
            )
            st.sidebar.success("Customer saved")

products = catalog.load_products(DATA_DIR)
product_names = [p.get("name", "").strip() for p in products if p.get("name")]
product_options = product_names + ["(manual)"]
default_product = "(manual)"
product_choice = st.sidebar.selectbox(
    "Product",
    product_options,
    index=product_options.index(default_product),
    key="product_select",
)

if product_choice != "(manual)":
    if st.session_state.get("_product_selected") != product_choice:
        selected = next((p for p in products if p.get("name", "").strip() == product_choice), None)
        if selected:
            st.session_state["item_name_input"] = selected.get("name", product_choice)
            st.session_state["unit_price_input"] = float(selected.get("unit_price", 0) or 0)
            st.session_state["vat_pct_input"] = float(selected.get("vat_pct", 0) or 0)
        st.session_state["_product_selected"] = product_choice

with st.form("receipt_form"):
    customer = st.text_input(t("customer", lang), key="customer_name_input")
    item_name = st.text_input(t("item", lang), key="item_name_input")
    qty = st.number_input(t("qty", lang), min_value=0.0, step=1.0, value=1.0, key="qty_input")
    unit_price = st.number_input(
        t("unit_price", lang),
        min_value=0.0,
        step=0.01,
        value=0.0,
        key="unit_price_input",
    )
    vat_pct = st.number_input(
        t("vat_pct", lang),
        min_value=0.0,
        step=0.1,
        value=24.0,
        key="vat_pct_input",
    )
    pay_method = st.text_input(t("pay_method", lang), key="pay_method_input")
    note = st.text_area(t("note", lang), key="note_input")
    generate_finvoice = st.checkbox("Generate Finvoice XML (OP manual upload)")
    submitted = st.form_submit_button(t("save", lang))

qty_dec = Decimal(str(qty))
unit_price_dec = Decimal(str(unit_price))
vat_pct_dec = Decimal(str(vat_pct))
totals = calculate_totals(qty_dec, unit_price_dec, vat_pct_dec)
subtotal = totals["subtotal"]
vat_amount = totals["vat_amount"]
total = totals["total"]

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
        "subtotal": str(subtotal),
        "vat_amount": str(vat_amount),
        "vat_pct": str(totals["vat_percent"]),
        "total": str(total),
        "currency": "EUR",
        "qty": str(qty_dec),
        "unit_price": str(unit_price_dec),
        "items": [
            {
                "name": item_name,
                "qty": str(qty_dec),
                "unit_price": str(unit_price_dec),
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
        finvoice_path = None
        finvoice_sha256 = None
        if generate_finvoice:
            exports_dir = (
                Path("storage") / f"{now.year:04d}" / f"{now.month:02d}" / "exports"
            )
            exports_dir.mkdir(parents=True, exist_ok=True)
            finvoice_path = exports_dir / f"finvoice_{receipt_no:06d}.xml"
            generate_finvoice_xml(str(finvoice_path), payload, company)
            finvoice_sha256 = ledger.compute_sha256(str(finvoice_path))
            st.success("Finvoice XML generated")
        excel_row = excel.save_row_to_excel(
            str(DATA_DIR / "ledger.xlsx"),
            {
                "receipt_no": receipt_no,
                "created_at": created_at,
                "customer": customer,
                "item": item_name,
                "qty": float(qty_dec),
                "unit_price": float(unit_price_dec),
                "vat_pct": float(totals["vat_percent"]),
                "subtotal": float(subtotal),
                "vat": float(vat_amount),
                "total": float(total),
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
                "finvoice_path": str(finvoice_path) if finvoice_path else None,
                "finvoice_sha256": finvoice_sha256,
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
        if finvoice_path:
            with open(finvoice_path, "rb") as handle:
                st.download_button(
                    "Download Finvoice XML",
                    data=handle.read(),
                    file_name=Path(finvoice_path).name,
                    mime="application/xml",
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
