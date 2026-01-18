type TotalsCardProps = {
  subtotal: string;
  vat: string;
  total: string;
  currency?: string;
};

const TotalsCard = ({ subtotal, vat, total, currency = "EUR" }: TotalsCardProps) => {
  return (
    <div className="card fade-in">
      <h3 className="section-title">Totals</h3>
      <div className="grid" style={{ gap: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span className="muted">Subtotal</span>
          <span>
            {subtotal} {currency}
          </span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span className="muted">VAT</span>
          <span>
            {vat} {currency}
          </span>
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontWeight: 700
          }}
        >
          <span>Total</span>
          <span>
            {total} {currency}
          </span>
        </div>
      </div>
    </div>
  );
};

export default TotalsCard;
