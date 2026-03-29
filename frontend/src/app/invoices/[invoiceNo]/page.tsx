"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";

import DownloadButtons from "../../../components/DownloadButtons";
import TotalsCard from "../../../components/TotalsCard";
import {
  getInvoiceLifecycle,
  getInvoiceTotals,
  type InvoiceLifecycleResponse,
  type InvoiceTotalsResponse
} from "../../../lib/api";

const InvoiceDetailPage = () => {
  const params = useParams<{ invoiceNo: string }>();
  const searchParams = useSearchParams();
  const invoiceNo = params.invoiceNo;
  const [lifecycle, setLifecycle] = useState<InvoiceLifecycleResponse | null>(null);
  const [lifecycleError, setLifecycleError] = useState("");
  const [totals, setTotals] = useState<InvoiceTotalsResponse | null>(null);
  const [totalsError, setTotalsError] = useState("");
  const subtotalQuery = searchParams.get("subtotal");
  const vatQuery = searchParams.get("vat");
  const totalQuery = searchParams.get("total");
  const currencyQuery = searchParams.get("currency");
  const hasQueryTotals =
    subtotalQuery !== null && vatQuery !== null && totalQuery !== null;

  useEffect(() => {
    let cancelled = false;

    const loadLifecycle = async () => {
      setLifecycle(null);
      setLifecycleError("");
      try {
        const response = await getInvoiceLifecycle(invoiceNo);
        if (!cancelled) {
          setLifecycle(response);
        }
      } catch (err) {
        if (!cancelled) {
          setLifecycle(null);
          setLifecycleError(err instanceof Error ? err.message : "Lifecycle lookup failed");
        }
      }
    };

    loadLifecycle();

    return () => {
      cancelled = true;
    };
  }, [invoiceNo]);

  useEffect(() => {
    let cancelled = false;
    setTotals(null);
    setTotalsError("");

    if (hasQueryTotals) {
      return;
    }

    const loadTotals = async () => {
      try {
        const response = await getInvoiceTotals(invoiceNo);
        if (!cancelled) {
          setTotals(response);
        }
      } catch (err) {
        if (!cancelled) {
          setTotalsError(err instanceof Error ? err.message : "Totals lookup failed");
        }
      }
    };

    loadTotals();

    return () => {
      cancelled = true;
    };
  }, [invoiceNo, hasQueryTotals, subtotalQuery, vatQuery, totalQuery, currencyQuery]);

  const subtotal = subtotalQuery || totals?.subtotal || "0.00";
  const vat = vatQuery || totals?.vat || "0.00";
  const total = totalQuery || totals?.total || "0.00";
  const currency = currencyQuery || totals?.currency || "EUR";
  const hasFinvoice = searchParams.get("has_finvoice") === "true";

  return (
    <div className="content fade-in">
      <section className="card">
        <h2 className="section-title">Invoice {invoiceNo}</h2>
        <p className="muted">Use the downloads below to fetch the generated files.</p>
        <div
          style={{
            marginTop: 12,
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
            padding: "6px 12px",
            borderRadius: 999,
            background: "rgba(255, 224, 102, 0.12)",
            color: "var(--color-accent)",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.04em"
          }}
        >
          Lifecycle status: {lifecycle?.status || (lifecycleError ? "unavailable" : "loading")}
        </div>
        {lifecycle?.status_changed_at ? (
          <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
            Status updated {lifecycle.status_changed_at}
          </div>
        ) : null}
        {totalsError ? (
          <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
            Totals lookup failed: {totalsError}
          </div>
        ) : null}
      </section>
      <div className="grid grid-two">
        <TotalsCard subtotal={subtotal} vat={vat} total={total} currency={currency} />
        <DownloadButtons invoiceNo={invoiceNo} hasFinvoice={hasFinvoice} />
      </div>
    </div>
  );
};

export default InvoiceDetailPage;
