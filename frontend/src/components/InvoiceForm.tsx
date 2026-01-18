"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { createInvoice } from "../lib/api";
import TotalsCard from "./TotalsCard";

const toFixed = (value: number) => value.toFixed(2);

const InvoiceForm = () => {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [customer, setCustomer] = useState({
    name: "",
    email: "",
    address: "",
    vat_id: ""
  });

  const [line, setLine] = useState({
    description: "",
    quantity: "1",
    unit_price: "0.00",
    vat_percent: "24.00"
  });

  const [paymentMethod, setPaymentMethod] = useState("");
  const [notes, setNotes] = useState("");
  const [generateFinvoice, setGenerateFinvoice] = useState(false);

  const qty = parseFloat(line.quantity || "0");
  const unit = parseFloat(line.unit_price || "0");
  const vatPct = parseFloat(line.vat_percent || "0");
  const subtotal = qty * unit;
  const vat = subtotal * (vatPct / 100);
  const total = subtotal + vat;

  const onSubmit = async () => {
    setSubmitting(true);
    setError("");
    try {
      const response = await createInvoice({
        customer,
        line,
        payment_method: paymentMethod,
        notes,
        options: { generate_finvoice: generateFinvoice, enable_backup: true }
      });
      const query = new URLSearchParams({
        subtotal: response.totals.subtotal_ex_vat || toFixed(subtotal),
        vat: response.totals.vat_amount || toFixed(vat),
        total: response.totals.total_inc_vat || toFixed(total),
        vat_percent: response.totals.vat_percent || line.vat_percent,
        currency: "EUR",
        has_finvoice: String(response.has_finvoice)
      });
      router.push(`/invoices/${response.invoice_no}?${query.toString()}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create invoice");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="grid grid-two fade-in">
      <div className="card">
        <h3 className="section-title">Create Invoice</h3>
        <div className="grid" style={{ gap: 12 }}>
          <input
            placeholder="Customer name"
            value={customer.name}
            onChange={(event) =>
              setCustomer({ ...customer, name: event.target.value })
            }
          />
          <input
            placeholder="Email"
            value={customer.email}
            onChange={(event) =>
              setCustomer({ ...customer, email: event.target.value })
            }
          />
          <input
            placeholder="Address"
            value={customer.address}
            onChange={(event) =>
              setCustomer({ ...customer, address: event.target.value })
            }
          />
          <input
            placeholder="VAT ID"
            value={customer.vat_id}
            onChange={(event) =>
              setCustomer({ ...customer, vat_id: event.target.value })
            }
          />
        </div>
        <div className="grid" style={{ gap: 12, marginTop: 20 }}>
          <input
            placeholder="Line description"
            value={line.description}
            onChange={(event) =>
              setLine({ ...line, description: event.target.value })
            }
          />
          <input
            placeholder="Quantity"
            value={line.quantity}
            onChange={(event) =>
              setLine({ ...line, quantity: event.target.value })
            }
          />
          <input
            placeholder="Unit price"
            value={line.unit_price}
            onChange={(event) =>
              setLine({ ...line, unit_price: event.target.value })
            }
          />
          <input
            placeholder="VAT percent"
            value={line.vat_percent}
            onChange={(event) =>
              setLine({ ...line, vat_percent: event.target.value })
            }
          />
          <input
            placeholder="Payment method"
            value={paymentMethod}
            onChange={(event) => setPaymentMethod(event.target.value)}
          />
          <textarea
            placeholder="Notes"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={3}
          />
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={generateFinvoice}
              onChange={(event) => setGenerateFinvoice(event.target.checked)}
            />
            Generate Finvoice XML (OP manual upload)
          </label>
          <button className="btn btn-primary" onClick={onSubmit} disabled={submitting}>
            {submitting ? "Creating..." : "Create invoice"}
          </button>
          {error ? <div className="muted">{error}</div> : null}
        </div>
      </div>
      <TotalsCard
        subtotal={toFixed(subtotal)}
        vat={toFixed(vat)}
        total={toFixed(total)}
      />
    </div>
  );
};

export default InvoiceForm;
