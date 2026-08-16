/**
 * Shared chrome for the public auth screens — prototype screens 02–05.
 *
 * The prototype draws each of these as a `.card` capped at 420px with an
 * `h3` title, a `.sub`, `.field` rows and a full-width primary button. The
 * card is centred on the `--bg` ground and carries the Scanwick mark, which
 * is also the route back to the marketing site.
 */

import { useState, type FormEvent, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { Eye, EyeOff } from "lucide-react";
import { PublicShell } from "@/features/shell/app-shell";
import { Btn, Card, Inp } from "@/components/sw";
import { env } from "@/lib/env";

export function AuthLayout({
  title,
  sub,
  children,
  alert,
  width = 420,
}: {
  title: string;
  sub?: ReactNode;
  children: ReactNode;
  alert?: ReactNode;
  width?: number;
}) {
  return (
    <PublicShell>
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px 20px 56px",
          gap: 16,
        }}
      >
        <Link
          to="/"
          style={{ display: "flex", gap: 10, alignItems: "center", textDecoration: "none", color: "inherit" }}
          aria-label="Scanwick home"
        >
          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: 7,
              background: "var(--g800)",
              color: "#fff",
              display: "grid",
              placeItems: "center",
              fontWeight: 800,
              fontSize: 15,
            }}
          >
            S
          </div>
          <b style={{ fontSize: 16, letterSpacing: "-.3px" }}>Scanwick</b>
        </Link>

        <div style={{ width: "100%", maxWidth: width }}>
          {alert}
          <div style={{ marginTop: alert ? 12 : 0 }}>
            <Card title={title} sub={sub} style={{ maxWidth: width, width: "100%" }}>
              {children}
            </Card>
          </div>
        </div>
      </div>
    </PublicShell>
  );
}

/**
 * Inline alert in the prototype's palette. Errors are amber-on-warn rather
 * than red where they are recoverable, and the copy never reveals whether
 * an email address exists.
 */
export function AuthAlert({ message, tone }: { message: string; tone: "success" | "failure" }) {
  const success = tone === "success";
  return (
    <div
      role="alert"
      style={{
        padding: "11px 14px",
        borderRadius: 8,
        fontSize: 12.5,
        border: `1px solid ${success ? "var(--g300)" : "#E9C6C6"}`,
        background: success ? "var(--g50)" : "var(--stopbg)",
        color: success ? "var(--g700)" : "var(--stop)",
        fontWeight: 600,
      }}
    >
      {message}
    </div>
  );
}

/** Password field with the visibility control the form spec calls for. */
export function PasswordInput({
  id,
  value,
  onChange,
  onBlur,
  name,
  placeholder,
  invalid,
  autoComplete,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  name?: string;
  placeholder?: string;
  invalid?: boolean;
  autoComplete?: string;
}) {
  const [shown, setShown] = useState(false);
  return (
    <div style={{ position: "relative" }}>
      <Inp
        id={id}
        name={name}
        type={shown ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        placeholder={placeholder}
        invalid={invalid}
        autoComplete={autoComplete}
        style={{ paddingRight: 40 }}
      />
      <button
        type="button"
        onClick={() => setShown((v) => !v)}
        aria-label={shown ? "Hide password" : "Show password"}
        style={{
          position: "absolute",
          right: 10,
          top: "50%",
          transform: "translateY(-50%)",
          background: "none",
          border: 0,
          padding: 4,
          cursor: "pointer",
          color: "var(--ink3)",
          display: "grid",
          placeItems: "center",
        }}
      >
        {shown ? <EyeOff size={15} strokeWidth={2.2} /> : <Eye size={15} strokeWidth={2.2} />}
      </button>
    </div>
  );
}

/**
 * Google sign-in. Screen 67 lists Google as a connectable sign-in method,
 * so the existing OAuth entry point is kept — restyled as a secondary
 * button under the prototype's separator treatment.
 */
export function GoogleAuth({ label = "Continue with Google" }: { label?: string }) {
  return (
    <>
      <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "16px 0 12px" }}>
        <span style={{ flex: 1, height: 1, background: "var(--line)" }} />
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: "0.6px",
            textTransform: "uppercase",
            color: "var(--ink3)",
          }}
        >
          or
        </span>
        <span style={{ flex: 1, height: 1, background: "var(--line)" }} />
      </div>
      <Btn
        tone="sec"
        block
        onClick={() => {
          window.location.href = `${env.authApiBaseUrl}/api/auth/google`;
        }}
      >
        <svg viewBox="0 0 48 48" width="15" height="15" aria-hidden="true">
          <path
            fill="#EA4335"
            d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
          />
          <path
            fill="#4285F4"
            d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
          />
          <path
            fill="#FBBC05"
            d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
          />
          <path
            fill="#34A853"
            d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
          />
        </svg>
        {label}
      </Btn>
    </>
  );
}

/**
 * Six separate code boxes — prototype screen 04. Typing advances, backspace
 * on an empty box steps back, and a pasted code fills the row.
 */
export function OtpBoxes({
  value,
  onChange,
  length = 6,
  autoFocus = true,
}: {
  value: string;
  onChange: (value: string) => void;
  length?: number;
  autoFocus?: boolean;
}) {
  const digits = value.padEnd(length, " ").slice(0, length).split("");

  function setAt(index: number, digit: string) {
    const next = digits.map((d, i) => (i === index ? digit : d)).join("").replace(/\s+$/, "");
    onChange(next.trim());
  }

  return (
    <div style={{ display: "flex", gap: 8, justifyContent: "center", margin: "18px 0" }}>
      {digits.map((digit, index) => (
        <input
          key={index}
          className="inp"
          inputMode="numeric"
          autoComplete={index === 0 ? "one-time-code" : "off"}
          autoFocus={autoFocus && index === 0}
          aria-label={`Digit ${index + 1}`}
          maxLength={1}
          value={digit.trim()}
          style={{ width: 44, textAlign: "center", fontSize: 19, fontFamily: "var(--mono)", padding: "10px 4px" }}
          onChange={(e) => {
            const typed = e.target.value.replace(/\D/g, "");
            if (!typed) {
              setAt(index, " ");
              return;
            }
            setAt(index, typed[typed.length - 1]);
            const next = e.target.parentElement?.children[index + 1] as HTMLInputElement | undefined;
            next?.focus();
          }}
          onKeyDown={(e) => {
            if (e.key === "Backspace" && !digit.trim()) {
              const prev = e.currentTarget.parentElement?.children[index - 1] as HTMLInputElement | undefined;
              prev?.focus();
            }
          }}
          onPaste={(e) => {
            const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, length);
            if (!pasted) return;
            e.preventDefault();
            onChange(pasted);
          }}
        />
      ))}
    </div>
  );
}

/** a•••••e.n@example.com — the prototype's own masking on screen 04. */
export function maskEmail(email: string): string {
  const [local, domain] = email.split("@");
  if (!domain || local.length < 3) return email;
  return `${local[0]}${"•".repeat(Math.max(1, local.length - 2))}${local[local.length - 1]}@${domain}`;
}

/** Centred footer line: "Already have an account? Sign in". */
export function AuthFootLink({
  desc,
  link,
  to,
  onClick,
}: {
  desc: string;
  link: string;
  to?: string;
  onClick?: () => void;
}) {
  return (
    <div className="hint" style={{ textAlign: "center", marginTop: 12 }}>
      {desc}{" "}
      {to ? (
        <Link to={to} style={{ color: "var(--g700)", fontWeight: 600 }}>
          {link}
        </Link>
      ) : (
        <button
          type="button"
          onClick={onClick}
          style={{ background: "none", border: 0, padding: 0, font: "inherit", color: "var(--g700)", fontWeight: 600, cursor: "pointer" }}
        >
          {link}
        </button>
      )}
    </div>
  );
}

/** Submits on Enter and prevents the default page reload. */
export function AuthForm({ onSubmit, children }: { onSubmit: (e: FormEvent) => void; children: ReactNode }) {
  return <form onSubmit={onSubmit}>{children}</form>;
}
