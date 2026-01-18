"use client";

import { useParams, useSearchParams } from "next/navigation";

import DownloadButtons from "../../../components/DownloadButtons";
import TotalsCard from "../../../components/TotalsCard";

const InvoiceDetailPage = () => {
  const params = useParams<{ invoiceNo: string }>();
  const searchParams = useSearchParams();
  const invoiceNo = params.invoiceNo;

  const subtotal = searchParams.get("subtotal") || "0.00";
  const vat = searchParams.get("vat") || "0.00";
  const total = searchParams.get("total") || "0.00";
  const currency = searchParams.get("currency") || "EUR";
  const hasFinvoice = searchParams.get("has_finvoice") === "true";

  return (
    <div className="content fade-in">
      <section className="card">
        <h2 className="section-title">Invoice {invoiceNo}</h2>
        <p className="muted">Use the downloads below to fetch the generated files.</p>
      </section>
      <div className="grid grid-two">
        <TotalsCard subtotal={subtotal} vat={vat} total={total} currency={currency} />
        <DownloadButtons invoiceNo={invoiceNo} hasFinvoice={hasFinvoice} />
      </div>
    </div>
  );
};

export default InvoiceDetailPage;
