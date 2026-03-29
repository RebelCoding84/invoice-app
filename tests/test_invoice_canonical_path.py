from __future__ import annotations

import asyncio
import base64
import contextlib
import copy
import json
import importlib.util
import os
import sys
import unittest
from types import SimpleNamespace
import types
import zlib
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

from fastapi import HTTPException

import core.invoice_service as invoice_service
import server.main as server_main
import server.security as server_security
import storage.catalog as catalog
import storage.excel as excel
import storage.ledger as ledger
import config as app_config
import utils.i18n as i18n
from core.models import Customer, InvoiceDraft, InvoiceLine, InvoiceOptions, InvoiceStatus
from server.schemas import InvoiceCreateRequest


def _business_issue_date() -> datetime:
    return datetime(2026, 1, 15, 12, 0, 0)


def _build_draft() -> InvoiceDraft:
    issue_date = _business_issue_date()
    due_date = issue_date + timedelta(days=14)
    return InvoiceDraft(
        customer=Customer(
            name="Acme Oy",
            email="billing@example.com",
            address="Test Street 1",
            vat_id="FI12345678",
        ),
        line=InvoiceLine(
            description="Consulting service",
            quantity=Decimal("2"),
            unit_price=Decimal("10.00"),
            vat_percent=Decimal("24.00"),
        ),
        payment_method="bank transfer",
        notes="PO-2026-0001",
        currency="EUR",
        issue_date=issue_date,
        due_date=due_date,
    )


def _build_request_payload() -> dict:
    issue_date = _business_issue_date()
    due_date = issue_date + timedelta(days=14)
    return {
        "customer": {
            "name": "Acme Oy",
            "email": "billing@example.com",
            "address": "Test Street 1",
            "vat_id": "FI12345678",
        },
        "line": {
            "description": "Consulting service",
            "quantity": "2",
            "unit_price": "10.00",
            "vat_percent": "24.00",
        },
        "payment_method": "bank transfer",
        "notes": "PO-2026-0001",
        "currency": "EUR",
        "issue_date": issue_date.isoformat(),
        "due_date": due_date.isoformat(),
        "options": {
            "generate_finvoice": False,
            "enable_backup": False,
        },
    }


def _extract_reportlab_text(pdf_bytes: bytes) -> str:
    marker = b"/Filter [ /ASCII85Decode /FlateDecode ]"
    pieces: list[str] = []
    offset = 0

    while True:
        marker_index = pdf_bytes.find(marker, offset)
        if marker_index == -1:
            break

        stream_index = pdf_bytes.find(b"stream", marker_index)
        endstream_index = pdf_bytes.find(b"endstream", stream_index)
        if stream_index == -1 or endstream_index == -1:
            break

        raw_stream = pdf_bytes[stream_index + len(b"stream") : endstream_index].strip(
            b"\r\n"
        )
        if raw_stream.endswith(b"~>"):
            raw_stream = raw_stream[:-2]

        try:
            decoded = base64.a85decode(
                raw_stream, adobe=False, ignorechars=b"\n\r\t "
            )
            inflated = zlib.decompress(decoded)
        except Exception:
            offset = endstream_index + len(b"endstream")
            continue

        pieces.append(inflated.decode("latin-1"))
        offset = endstream_index + len(b"endstream")

    return "\n".join(pieces)


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _asgi_options_request(
    app,
    path: str,
    headers: dict[str, str],
) -> tuple[int, dict[str, str], bytes]:
    status_code: int | None = None
    response_headers: dict[str, str] = {}
    response_body = bytearray()
    request_sent = False

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        nonlocal status_code, response_headers
        if message["type"] == "http.response.start":
            status_code = message["status"]
            response_headers = {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in message.get("headers", [])
            }
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "OPTIONS",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in headers.items()
        ],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "root_path": "",
    }

    asyncio.run(app(scope, receive, send))

    return status_code or 500, response_headers, bytes(response_body)


@contextlib.contextmanager
def _invoice_runtime(tmp_path: Path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(invoice_service, "DATA_DIR", tmp_path / "data"))
            stack.enter_context(patch.object(invoice_service, "BACKUP_DIR", tmp_path / "backups"))
            stack.enter_context(patch.object(invoice_service, "BACKUP_ENABLED", False))
            stack.enter_context(patch.object(invoice_service, "COMPANY_NAME", "Test Co"))
            stack.enter_context(patch.object(invoice_service, "COMPANY_ADDRESS", "Main Street 1"))
            stack.enter_context(patch.object(invoice_service, "COMPANY_ID", "1234567-8"))
            stack.enter_context(patch.object(invoice_service, "COMPANY_VAT", "FI12345678"))
            stack.enter_context(patch.object(invoice_service, "COMPANY_EMAIL", "info@example.com"))
            stack.enter_context(patch.object(invoice_service, "COMPANY_PHONE", "+358000000"))
            stack.enter_context(patch.object(invoice_service, "COMPANY_WEB", "https://example.com"))
            stack.enter_context(patch.object(server_security, "API_KEY", "dev-key"))
            yield
    finally:
        os.chdir(old_cwd)


@contextlib.contextmanager
def _render_spy():
    calls: list[dict] = []
    original_render = invoice_service.render_receipt_pdf

    def capture_render(output_path: str, payload: dict, company: dict) -> bytes:
        calls.append(
            {
                "output_path": output_path,
                "payload": copy.deepcopy(payload),
                "company": copy.deepcopy(company),
            }
        )
        return original_render(output_path, payload, company)

    with patch.object(invoice_service, "render_receipt_pdf", capture_render):
        yield calls


@contextlib.contextmanager
def _import_lite_app_with_fakes(
    tmp_path: Path,
    customers: list[dict],
    customer_choice: str,
):
    fake_streamlit = types.ModuleType("streamlit")
    fake_streamlit.session_state = {}
    captured: dict[str, object] = {"writes": []}

    class FakeSidebar:
        def selectbox(self, label, options, index=0, key=None):
            if label == "Language":
                return "fi"
            if label == "Provider":
                return "local"
            if label == "Customer":
                return customer_choice
            if label == "Product":
                return "(manual)"
            return options[index]

        def checkbox(self, *args, **kwargs):
            return False

        def text_input(self, *args, **kwargs):
            return ""

        def button(self, *args, **kwargs):
            return False

        def write(self, *args, **kwargs):
            return None

        def success(self, *args, **kwargs):
            return None

    @contextlib.contextmanager
    def fake_form(_name):
        yield

    fake_streamlit.sidebar = FakeSidebar()
    fake_streamlit.set_page_config = lambda *args, **kwargs: None
    fake_streamlit.title = lambda *args, **kwargs: None
    fake_streamlit.form = fake_form
    fake_streamlit.text_input = lambda *args, **kwargs: fake_streamlit.session_state.get(
        kwargs.get("key", ""), ""
    )
    fake_streamlit.number_input = lambda *args, **kwargs: kwargs.get("value")
    fake_streamlit.text_area = lambda *args, **kwargs: ""
    fake_streamlit.checkbox = lambda *args, **kwargs: False
    fake_streamlit.form_submit_button = lambda *args, **kwargs: True
    fake_streamlit.subheader = lambda *args, **kwargs: None
    fake_streamlit.write = lambda *args, **kwargs: captured["writes"].append(
        " ".join(str(arg) for arg in args)
    )
    fake_streamlit.download_button = lambda *args, **kwargs: None
    fake_streamlit.success = lambda *args, **kwargs: None
    fake_streamlit.error = lambda *args, **kwargs: None
    fake_streamlit.exception = lambda *args, **kwargs: None

    def fake_create_invoice(draft, options):
        captured["draft"] = draft
        captured["options"] = options
        return SimpleNamespace(
            artifacts=SimpleNamespace(
                pdf_bytes=b"%PDF-1.4",
                finvoice_bytes=None,
                invoice_no="1",
            ),
            lifecycle=SimpleNamespace(
                status=InvoiceStatus.ISSUED,
                changed_at=_business_issue_date(),
            ),
            paths={
                "pdf_path": str(tmp_path / "receipt_000001.pdf"),
                "finvoice_path": None,
            },
            totals={},
        )

    with patch.object(app_config, "LOG_DIR", tmp_path / "logs"), patch.object(
        app_config, "DATA_DIR", tmp_path / "data"
    ), patch.object(catalog, "load_customers", return_value=customers), patch.object(
        catalog, "load_products", return_value=[]
    ), patch.object(
        i18n, "load_locale", return_value="fi"
    ), patch.object(
        i18n, "t", side_effect=lambda key, lang: key
    ), patch.object(
        invoice_service, "create_invoice", side_effect=fake_create_invoice
    ), patch.dict(
        sys.modules, {"streamlit": fake_streamlit}
    ):
        spec = importlib.util.spec_from_file_location("app_under_test", Path("app.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            assert spec.loader is not None
            spec.loader.exec_module(module)
            yield module, captured
        finally:
            sys.modules.pop(spec.name, None)


class TestInvoiceCanonicalPath(unittest.TestCase):
    def test_create_invoice_uses_canonical_payload_and_renders_invoice_number(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            with _invoice_runtime(tmp_path), _render_spy() as render_calls:
                result = invoice_service.create_invoice(
                    _build_draft(),
                    InvoiceOptions(generate_finvoice=True, enable_backup=False),
                )
                pdf_path = Path(result.paths["pdf_path"]).resolve()
                pdf_bytes = pdf_path.read_bytes()

            self.assertEqual(result.artifacts.invoice_no, "1")
            self.assertEqual(Path(result.paths["pdf_path"]).name, "receipt_000001.pdf")
            self.assertEqual(Path(result.paths["finvoice_path"]).name, "finvoice_000001.xml")
            self.assertEqual(len(render_calls), 1)
            self.assertIsNotNone(result.artifacts.finvoice_bytes)

            payload = render_calls[0]["payload"]
            company = render_calls[0]["company"]
            self.assertEqual(payload["invoice_no"], result.artifacts.invoice_no)
            self.assertEqual(payload["receipt_no"], result.artifacts.invoice_no)
            self.assertEqual(payload["customer"]["name"], "Acme Oy")
            self.assertEqual(payload["totals"]["total_inc_vat"], Decimal("24.80"))
            self.assertEqual(company["name"], "Test Co")
            self.assertEqual(company["id"], "1234567-8")
            self.assertEqual(company["vat"], "FI12345678")
            self.assertEqual(company["address"], "Main Street 1")
            self.assertEqual(company["email"], "info@example.com")
            self.assertEqual(company["phone"], "+358000000")
            self.assertEqual(company["web"], "https://example.com")

            pdf_text = _extract_reportlab_text(pdf_bytes)
            self.assertIn(f"Invoice #: {result.artifacts.invoice_no}", pdf_text)
            self.assertIn("Company: Test Co", pdf_text)
            self.assertIn("Company ID: 1234567-8", pdf_text)
            self.assertIn("Company VAT: FI12345678", pdf_text)
            self.assertIn("Company address: Main Street 1", pdf_text)
            self.assertIn("Company email: info@example.com", pdf_text)
            self.assertIn("Company phone: +358000000", pdf_text)
            self.assertIn("Company web: https://example.com", pdf_text)
            self.assertIn("Customer: Acme Oy", pdf_text)
            self.assertIn("Customer address: Test Street 1", pdf_text)
            self.assertIn("Customer email: billing@example.com", pdf_text)
            self.assertIn("Customer VAT ID: FI12345678", pdf_text)

            finvoice_root = ET.fromstring(result.artifacts.finvoice_bytes)
            self.assertEqual(
                finvoice_root.findtext("InvoiceNumber"),
                result.artifacts.invoice_no,
            )
            self.assertEqual(
                finvoice_root.findtext("SellerPartyDetails/SellerPartyName"),
                "Test Co",
            )
            self.assertEqual(
                finvoice_root.findtext("SellerPartyDetails/SellerPartyIdentifier"),
                "1234567-8",
            )

    def test_create_invoice_sets_issued_status_and_persists_it(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            with _invoice_runtime(tmp_path):
                result = invoice_service.create_invoice(
                    _build_draft(),
                    InvoiceOptions(generate_finvoice=True, enable_backup=False),
                )

            ledger_path = (
                tmp_path / "storage" / "2026-01" / "meta" / "ledger_2026-01.jsonl"
            )
            entries = _read_jsonl(ledger_path)

            self.assertEqual(result.lifecycle.status, InvoiceStatus.ISSUED)
            self.assertEqual(result.lifecycle.changed_at, _business_issue_date())
            self.assertGreaterEqual(len(entries), 1)
            self.assertEqual(entries[-1]["event_type"], "SUCCESS")
            self.assertEqual(entries[-1]["status"], "issued")
            self.assertEqual(
                entries[-1]["status_changed_at"], _business_issue_date().isoformat()
            )

    def test_fastapi_create_invoice_and_pdf_download_round_trip(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            with _invoice_runtime(tmp_path):
                request_model = InvoiceCreateRequest.model_validate(_build_request_payload())
                create_response = server_main.create_invoice_endpoint(request_model)

                self.assertEqual(create_response.invoice_no, "1")
                self.assertFalse(create_response.has_finvoice)
                self.assertEqual(create_response.totals["subtotal_ex_vat"], "20.00")
                self.assertEqual(create_response.totals["total_inc_vat"], "24.80")

                pdf_response = server_main.get_invoice_pdf(
                    create_response.invoice_no
                )
                pdf_path = Path(pdf_response.path).resolve()
                pdf_bytes = pdf_path.read_bytes()

            self.assertEqual(pdf_response.media_type, "application/pdf")
            self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_failed_invoice_event_persists_draft_status(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            with _invoice_runtime(tmp_path), patch.object(
                invoice_service,
                "render_receipt_pdf",
                side_effect=RuntimeError("boom"),
            ):
                with self.assertRaises(RuntimeError):
                    invoice_service.create_invoice(
                        _build_draft(),
                        InvoiceOptions(generate_finvoice=False, enable_backup=False),
                    )

            ledger_path = (
                tmp_path / "storage" / "2026-01" / "meta" / "ledger_2026-01.jsonl"
            )
            entries = _read_jsonl(ledger_path)

            self.assertGreaterEqual(len(entries), 1)
            self.assertEqual(entries[-1]["event_type"], "FAILED")
            self.assertEqual(entries[-1]["status"], "draft")
            self.assertEqual(
                entries[-1]["status_changed_at"], _business_issue_date().isoformat()
            )

    def test_lite_selected_customer_passes_full_metadata_to_core(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            customers = [
                {
                    "name": "Acme Oy",
                    "email": "billing@example.com",
                    "address": "Test Street 1",
                    "vat_id": "FI12345678",
                }
            ]
            with _import_lite_app_with_fakes(
                tmp_path,
                customers=customers,
                customer_choice="Acme Oy",
            ) as (_, captured):
                draft = captured["draft"]

            self.assertEqual(draft.customer.name, "Acme Oy")
            self.assertEqual(draft.customer.email, "billing@example.com")
            self.assertEqual(draft.customer.address, "Test Street 1")
            self.assertEqual(draft.customer.vat_id, "FI12345678")

    def test_invoice_status_transition_helper_validates_allowed_transitions(self):
        self.assertEqual(
            invoice_service.validate_invoice_status_transition(
                InvoiceStatus.DRAFT, InvoiceStatus.ISSUED
            ),
            InvoiceStatus.ISSUED,
        )
        self.assertEqual(
            invoice_service.validate_invoice_status_transition(
                InvoiceStatus.ISSUED, InvoiceStatus.CANCELLED
            ),
            InvoiceStatus.CANCELLED,
        )
        with self.assertRaisesRegex(ValueError, "Invalid invoice status transition"):
            invoice_service.validate_invoice_status_transition(
                InvoiceStatus.PAID, InvoiceStatus.ISSUED
            )

    def test_invoice_lifecycle_lookup_returns_latest_matching_event(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            with _invoice_runtime(tmp_path):
                first_changed_at = _business_issue_date()
                second_changed_at = first_changed_at + timedelta(days=45)

                ledger.append_event(
                    first_changed_at,
                    {
                        "event_type": "SUCCESS",
                        "invoice_no": 1,
                        "receipt_no": 1,
                        "created_at": first_changed_at.isoformat(),
                        "status": "issued",
                        "status_changed_at": first_changed_at.isoformat(),
                    },
                )
                ledger.append_event(
                    second_changed_at,
                    {
                        "event_type": "SUCCESS",
                        "invoice_no": 1,
                        "receipt_no": 1,
                        "created_at": second_changed_at.isoformat(),
                        "status": "paid",
                        "status_changed_at": second_changed_at.isoformat(),
                    },
                )

                metadata = ledger.read_invoice_lifecycle_metadata("0001")
                response = server_main.get_invoice_lifecycle("1")

            self.assertIsNotNone(metadata)
            assert metadata is not None
            self.assertEqual(metadata["invoice_no"], "1")
            self.assertEqual(metadata["status"], InvoiceStatus.PAID)
            self.assertEqual(metadata["status_changed_at"], second_changed_at)
            self.assertEqual(response.invoice_no, "1")
            self.assertEqual(response.status, InvoiceStatus.PAID)
            self.assertEqual(response.status_changed_at, second_changed_at)

    def test_invoice_totals_lookup_returns_ledger_values(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            with _invoice_runtime(tmp_path):
                result = invoice_service.create_invoice(
                    _build_draft(),
                    InvoiceOptions(generate_finvoice=False, enable_backup=False),
                )

                ledger_totals = excel.read_invoice_totals(
                    tmp_path / "data" / "ledger.xlsx",
                    result.artifacts.invoice_no,
                )
                response = server_main.get_invoice_totals("0001")

            self.assertIsNotNone(ledger_totals)
            assert ledger_totals is not None
            self.assertEqual(ledger_totals["invoice_no"], "1")
            self.assertEqual(ledger_totals["subtotal"], "20.00")
            self.assertEqual(ledger_totals["vat"], "4.80")
            self.assertEqual(ledger_totals["total"], "24.80")
            self.assertEqual(ledger_totals["currency"], "EUR")
            self.assertEqual(response.invoice_no, "1")
            self.assertEqual(response.subtotal, "20.00")
            self.assertEqual(response.vat, "4.80")
            self.assertEqual(response.total, "24.80")
            self.assertEqual(response.currency, "EUR")

    def test_invoice_totals_lookup_returns_client_error_for_missing_invoice(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            with _invoice_runtime(tmp_path), self.assertRaises(HTTPException) as ctx:
                server_main.get_invoice_totals("999")

            self.assertEqual(ctx.exception.status_code, 404)
            self.assertEqual(ctx.exception.detail, "Invoice totals not found")

    def test_fastapi_create_invoice_validation_failure_returns_client_error(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            with _invoice_runtime(tmp_path), patch.object(
                invoice_service, "COMPANY_ID", ""
            ), _render_spy() as render_calls:
                payload = _build_request_payload()
                payload["options"]["generate_finvoice"] = True
                request_model = InvoiceCreateRequest.model_validate(payload)

                with self.assertRaises(HTTPException) as ctx:
                    server_main.create_invoice_endpoint(request_model)

            self.assertEqual(ctx.exception.status_code, 422)
            self.assertEqual(
                ctx.exception.detail,
                "Company identifier is required for Finvoice generation",
            )
            self.assertEqual(render_calls, [])

    def test_lite_success_branch_displays_lifecycle_status(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            customers = [
                {
                    "name": "Acme Oy",
                    "email": "billing@example.com",
                    "address": "Test Street 1",
                    "vat_id": "FI12345678",
                }
            ]
            with _import_lite_app_with_fakes(
                tmp_path,
                customers=customers,
                customer_choice="Acme Oy",
            ) as (_, captured):
                writes = captured["writes"]

            self.assertTrue(
                any("Lifecycle status: issued" in str(message) for message in writes)
            )

    def test_company_metadata_validation_blocks_missing_required_fields(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)

            with self.subTest("missing company name"):
                with _invoice_runtime(tmp_path), patch.object(
                    invoice_service, "COMPANY_NAME", ""
                ), _render_spy() as render_calls:
                    with self.assertRaisesRegex(
                        ValueError, "Company name is required for PDF generation"
                    ):
                        invoice_service.create_invoice(
                            _build_draft(),
                            InvoiceOptions(
                                generate_finvoice=False, enable_backup=False
                            ),
                        )
                self.assertEqual(render_calls, [])
                self.assertFalse((tmp_path / "data" / "sequence.txt").exists())

            with self.subTest("missing company identifier for finvoice"):
                with _invoice_runtime(tmp_path), patch.object(
                    invoice_service, "COMPANY_ID", ""
                ), _render_spy() as render_calls:
                    with self.assertRaisesRegex(
                        ValueError,
                        "Company identifier is required for Finvoice generation",
                    ):
                        invoice_service.create_invoice(
                            _build_draft(),
                            InvoiceOptions(generate_finvoice=True, enable_backup=False),
                        )
                self.assertEqual(render_calls, [])
                self.assertFalse((tmp_path / "data" / "sequence.txt").exists())

    def test_cors_preflight_allows_local_dev_origins_and_headers(self):
        status_code, response_headers, _ = _asgi_options_request(
            server_main.app,
            "/api/v1/invoices",
            {
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type, x-api-key",
            },
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(
            response_headers["access-control-allow-origin"],
            "http://localhost:3000",
        )
        allow_methods = response_headers["access-control-allow-methods"].lower()
        self.assertIn("get", allow_methods)
        self.assertIn("post", allow_methods)
        self.assertIn("options", allow_methods)
        allow_headers = response_headers["access-control-allow-headers"].lower()
        self.assertIn("content-type", allow_headers)
        self.assertIn("x-api-key", allow_headers)

    def test_api_and_direct_core_paths_produce_same_canonical_payload(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            with _invoice_runtime(tmp_path), _render_spy() as render_calls, patch.object(
                invoice_service, "_next_invoice_no", lambda seq_path: 7
            ):
                direct_result = invoice_service.create_invoice(
                    _build_draft(),
                    InvoiceOptions(generate_finvoice=False, enable_backup=False),
                )
                api_response = server_main.create_invoice_endpoint(
                    InvoiceCreateRequest.model_validate(_build_request_payload())
                )

            self.assertEqual(direct_result.artifacts.invoice_no, "7")
            self.assertEqual(api_response.invoice_no, "7")
            self.assertEqual(len(render_calls), 2)

            direct_payload = render_calls[0]["payload"]
            api_payload = render_calls[1]["payload"]

            canonical_keys = (
                "invoice_no",
                "issue_date",
                "due_date",
                "customer",
                "line",
                "totals",
                "payment_method",
                "notes",
                "reference",
                "currency",
            )
            for key in canonical_keys:
                self.assertEqual(direct_payload[key], api_payload[key])

            self.assertEqual(direct_payload["invoice_no"], direct_payload["receipt_no"])
            self.assertEqual(api_payload["invoice_no"], api_payload["receipt_no"])


if __name__ == "__main__":
    unittest.main()
