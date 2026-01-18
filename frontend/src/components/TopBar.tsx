import { brand } from "../lib/brand";

const TopBar = () => {
  return (
    <header className="card fade-in" style={{ margin: "16px 16px 0" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <div>
          <div
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: 28,
              fontWeight: 600
            }}
          >
            {brand.name}
          </div>
          <div className="muted" style={{ marginTop: 4 }}>
            Pro UI dashboard for the Rebel Invoice core service.
          </div>
        </div>
        <div
          style={{
            alignSelf: "center",
            padding: "6px 12px",
            borderRadius: 999,
            background: "rgba(255, 224, 102, 0.12)",
            color: "var(--color-accent)",
            fontWeight: 600
          }}
        >
            Local-first
        </div>
      </div>
    </header>
  );
};

export default TopBar;
