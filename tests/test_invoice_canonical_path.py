from __future__ import annotations

import asyncio
import base64
import contextlib
import copy
import os
import unittest
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
from core.models import Customer, InvoiceDraft, InvoiceLine, InvoiceOptions
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
