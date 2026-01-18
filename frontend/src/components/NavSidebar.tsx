import Link from "next/link";

import { brand } from "../lib/brand";

const NavSidebar = () => {
  return (
    <aside className="sidebar card" style={{ margin: 16 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{brand.logo.text}</div>
          <div className="muted" style={{ fontSize: 13 }}>
            {brand.logo.tagline}
          </div>
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <Link href="/">Dashboard</Link>
          <Link href="/invoices/new">New Invoice</Link>
          <Link href="/settings">Settings</Link>
        </nav>
        <div className="muted" style={{ fontSize: 12 }}>
          API ready for local workflows.
        </div>
      </div>
    </aside>
  );
};

export default NavSidebar;
