import type { Metadata } from "next";
import { Space_Grotesk, Fraunces } from "next/font/google";

import NavSidebar from "../components/NavSidebar";
import TopBar from "../components/TopBar";
import "./globals.css";

const sans = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-sans"
});

const serif = Fraunces({
  subsets: ["latin"],
  variable: "--font-serif"
});

export const metadata: Metadata = {
  title: "Rebel Invoice Pro UI",
  description: "Local-first invoice control panel"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${serif.variable}`}>
      <body>
        <div className="app-shell">
          <NavSidebar />
          <div className="content">
            <TopBar />
            <main>{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
