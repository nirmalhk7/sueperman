import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import "./globals.css";
export const metadata: Metadata = {
  title: "Sueperman — Your consumer-rights agent",
  description:
    "Evidence-backed recall discovery and locally approved remedy drafts.",
  icons: {
    icon: "/sueperman-receipt-logo.png",
    apple: "/sueperman-receipt-logo.png",
  },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  const sharedDemo = process.env.NEXT_PUBLIC_SHARED_DEMO === "true";
  return (
    <html lang="en">
      <body>
        <a className="skip" href="#main">
          Skip to content
        </a>
        <header>
          <Link className="brand" href="/">
            <Image
              src="/sueperman-receipt-logo.png"
              alt=""
              width={44}
              height={44}
              preload
            />
            Sueperman
          </Link>
          <nav aria-label="Primary">
            <Link href="/#purchases">My purchases</Link>
            <Link href="/#opportunities">Opportunities</Link>
            <Link href="/#activity">Activity</Link>
            <Link href="/demo-login">Demo sign in</Link>
          </nav>
          <span className="mode">{sharedDemo ? "SHARED DEMO" : "LOCAL"} / EVIDENCE FIRST</span>
        </header>
        <div className="banner">
          {sharedDemo
            ? "SHARED DEMO · Use synthetic purchases. Uploaded purchase details are shared with other visitors."
            : "REPLAY AVAILABLE · Demo purchases are synthetic. Source timestamps and provider modes shown on every result."}
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
