import Link from "next/link";

const DashboardPage = () => {
  return (
    <div className="content fade-in">
      <section className="card">
        <h2 className="section-title">Dashboard</h2>
        <p className="muted">
          This is a lightweight control panel for the Rebel Invoice FastAPI backend.
          Start by creating your first invoice.
        </p>
        <div style={{ marginTop: 16 }}>
          <Link className="btn btn-primary" href="/invoices/new">
            Create new invoice
          </Link>
        </div>
      </section>
      <section className="card">
        <h3 className="section-title">Recent activity</h3>
        <div className="muted">No synced invoices yet. Create one to get started.</div>
      </section>
    </div>
  );
};

export default DashboardPage;
