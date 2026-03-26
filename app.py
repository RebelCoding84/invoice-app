from __future__ import annotations

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from config import BACKUP_ENABLED, DATA_DIR, DEFAULT_LOCALE, DEFAULT_PROVIDER, LOG_DIR, TIMEZONE
from core.invoice_service import create_invoice
from core.models import Customer, InvoiceDraft, InvoiceLine, InvoiceOptions
from storage import catalog
from utils.i18n import load_locale, t
from utils.money import compute_totals


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


def _build_invoice_customer(
    customer_name: str,
    customer_choice: str,
    customers: list[dict],
) -> Customer:
    """Use saved customer metadata when the selected customer is available."""
    selected_customer = None
    if customer_choice != "(new)":
        selected_customer = next(
            (
                customer
                for customer in customers
                if customer.get("name", "").strip() == customer_choice.strip()
            ),
            None,
        )

    if selected_customer and customer_name.strip() == selected_customer.get("name", "").strip():
        return Customer(
            name=customer_name,
            email=selected_customer.get("email", "").strip(),
            address=selected_customer.get("address", "").strip(),
            vat_id=selected_customer.get("vat_id", "").strip(),
        )

    return Customer(name=customer_name, email="", address="", vat_id="")


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
totals = compute_totals(qty_dec, unit_price_dec, vat_pct_dec)
subtotal = totals["subtotal_ex_vat"]
vat_amount = totals["vat_amount"]
total = totals["total_inc_vat"]

st.subheader(t("preview", lang))
st.write(f"Subtotal: {subtotal:.2f} EUR")
st.write(f"VAT: {vat_amount:.2f} EUR")
st.write(f"Total: {total:.2f} EUR")

if submitted:
    now = _get_now()
    due_date = now + timedelta(days=14)

    draft = InvoiceDraft(
        customer=_build_invoice_customer(customer, customer_choice, customers),
        line=InvoiceLine(
            description=item_name,
            quantity=qty_dec,
            unit_price=unit_price_dec,
            vat_percent=vat_pct_dec,
        ),
        payment_method=pay_method,
        notes=note,
        currency="EUR",
        issue_date=now,
        due_date=due_date,
    )
    options = InvoiceOptions(
        generate_finvoice=generate_finvoice,
        enable_backup=BACKUP_ENABLED,
    )

    try:
        result = create_invoice(draft, options)
        st.success(t("saved", lang))
        pdf_name = Path(result.paths["pdf_path"]).name
        st.download_button(
            t("download_pdf", lang),
            data=result.artifacts.pdf_bytes,
            file_name=pdf_name,
            mime="application/pdf",
        )
        if result.artifacts.finvoice_bytes and result.paths.get("finvoice_path"):
            finvoice_name = Path(result.paths["finvoice_path"]).name
            st.download_button(
                "Download Finvoice XML",
                data=result.artifacts.finvoice_bytes,
                file_name=finvoice_name,
                mime="application/xml",
            )
        logger.info("Saved receipt %s", result.artifacts.invoice_no)
    except Exception as exc:
        logger.exception("Receipt save failed")
        st.error(str(exc))
