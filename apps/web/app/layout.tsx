import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import "./globals.css";
export const metadata: Metadata = {
  title: "Sueperman — Your consumer-rights agent",
  description:
    "Check your purchases against official recalls and prepare a remedy draft.",
  icons: {
    icon: "/sueperman-receipt-logo.png",
    apple: "/sueperman-receipt-logo.png",
  },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  const sharedWorkspace = process.env.NEXT_PUBLIC_SHARED_DEMO === "true";
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
            <span>Sueperman<span className="brand-dot">.</span></span>
          </Link>
          <nav aria-label="Primary">
            <Link href="/#purchases">My purchases</Link>
            <Link href="/#opportunities">Opportunities</Link>
            <Link href="/#activity">Activity</Link>
          </nav>
        </header>
        {sharedWorkspace && (
          <div className="banner">
            Uploaded purchase details are visible to other visitors.
          </div>
        )}
        <main id="main">{children}</main>
        <footer>
          <strong>Sueperman — Your consumer-rights agent</strong>
        </footer>
      </body>
    </html>
  );
}
