import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
export const metadata: Metadata = {
  title: "Sueperman — Your consumer-rights agent",
  description:
    "Evidence-backed recall discovery and locally approved remedy drafts.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a className="skip" href="#main">
          Skip to content
        </a>
        <header>
          <Link className="brand" href="/">
            <span className="monogram">S</span>Sueperman
          </Link>
          <nav aria-label="Primary">
            <Link href="/#purchases">My purchases</Link>
            <Link href="/#opportunities">Opportunities</Link>
            <Link href="/#activity">Activity</Link>
          </nav>
          <span className="mode">LOCAL / EVIDENCE FIRST</span>
        </header>
        <div className="banner">
          REPLAY AVAILABLE · Demo purchases are synthetic. Source timestamps and
          provider modes shown on every result.
        </div>
        <main id="main">{children}</main>
        <footer>
          <strong>Sueperman — Your consumer-rights agent</strong>
          <p>
            Sueperman helps organize public information and user-provided
            evidence; verify official terms and submit claims yourself.
          </p>
          <span>
            Local approval never sends a request. No legal advice or guaranteed
            remedy.
          </span>
        </footer>
      </body>
    </html>
  );
}
