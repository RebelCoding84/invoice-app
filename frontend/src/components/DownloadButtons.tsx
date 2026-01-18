"use client";

import { useState } from "react";

import { downloadFinvoice, downloadPdf } from "../lib/api";

type DownloadButtonsProps = {
  invoiceNo: string;
  hasFinvoice: boolean;
};

const triggerDownload = async (fileName: string, data: Blob) => {
  const url = URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
};

const DownloadButtons = ({ invoiceNo, hasFinvoice }: DownloadButtonsProps) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handlePdf = async () => {
    setLoading(true);
    setError("");
    try {
      const blob = await downloadPdf(invoiceNo);
      await triggerDownload(`receipt_${invoiceNo}.pdf`, blob);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setLoading(false);
    }
  };

  const handleFinvoice = async () => {
    setLoading(true);
    setError("");
    try {
      const blob = await downloadFinvoice(invoiceNo);
      await triggerDownload(`finvoice_${invoiceNo}.xml`, blob);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card fade-in">
      <h3 className="section-title">Downloads</h3>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <button className="btn btn-primary" onClick={handlePdf} disabled={loading}>
          Download PDF
        </button>
        {hasFinvoice ? (
          <button
            className="btn btn-secondary"
            onClick={handleFinvoice}
            disabled={loading}
          >
            Download Finvoice
          </button>
        ) : (
          <button className="btn btn-ghost" disabled>
            Finvoice not available
          </button>
        )}
      </div>
      {error ? <div className="muted" style={{ marginTop: 8 }}>{error}</div> : null}
    </div>
  );
};

export default DownloadButtons;
