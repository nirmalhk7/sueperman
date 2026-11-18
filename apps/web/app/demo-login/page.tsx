"use client";

import Link from "next/link";
import { useState, useSyncExternalStore } from "react";
import styles from "./page.module.css";

const subscribe = () => () => {};

export default function DemoLogin() {
  const [signedIn, setSignedIn] = useState(false);
  const ready = useSyncExternalStore(subscribe, () => true, () => false);
  return (
    <section className={styles.panel} aria-labelledby="demo-login-title">
      <p className={styles.eyebrow}>Synthetic visitor · Presentation only</p>
      <h1 id="demo-login-title">Demo sign in</h1>
      <p className={styles.notice}>
        No private account or data isolation. This form simulates sign-in only.
        Workspace records remain shared. Use synthetic purchases only.
      </p>
      {signedIn ? (
        <div className={styles.content}>
          <p role="status">Demo session started. You are viewing the shared workspace as a synthetic visitor.</p>
          <Link className={styles.continue} href="/">Continue to workspace</Link>
          <button type="button" className="secondary" onClick={() => setSignedIn(false)}>
            End demo session
          </button>
          <p>Ending this demo session changes this screen only. It does not lock, hide, or delete workspace records.</p>
        </div>
      ) : (
        <form className={styles.content} onSubmit={event => {
          event.preventDefault();
          setSignedIn(true);
        }}>
          <label htmlFor="demo-email">Demo email</label>
          <input id="demo-email" type="email" value="visitor@example.invalid" readOnly autoComplete="off" aria-describedby="demo-credentials" />
          <label htmlFor="demo-password">Demo password</label>
          <input id="demo-password" type="password" value="demo-only" readOnly autoComplete="off" aria-describedby="demo-credentials" />
          <p id="demo-credentials">Prefilled fake credentials. No real email or password needed; nothing is submitted.</p>
          <button type="submit" disabled={!ready}>Sign in to demo</button>
          <noscript>Demo sign-in requires JavaScript. You can still continue to the workspace.</noscript>
          <Link href="/">Continue without demo sign-in</Link>
        </form>
      )}
      <p className={styles.footnote}>No account is created. Reloading this page resets this simulated session.</p>
    </section>
  );
}
