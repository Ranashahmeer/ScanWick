/**
 * Public-site chrome — the nav bar and footer from prototype screen 01.
 *
 * Shared by the landing page, blog, contact and the legal pages so the
 * public surface is one design rather than several. `Header`/`Footer` keep
 * their original names because the not-yet-converted public pages import
 * them under those names.
 */

import { useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { useAuth } from "@/hooks/use-auth";

export const SOURCES =
  "OPay · PalmPay · Kuda · Moniepoint · Wema · GTBank · UBA · Zenith · First Bank · Sterling · Access · Stanbic IBTC · Alpha Morgan";

export const navLinks = [
  ["For individuals", "/#individuals"],
  ["For lenders", "/#lenders"],
  ["Security", "/#trust"],
  ["Pricing", "/#pricing"],
  ["About", "/about"],
] as const;

export const footerColumns = [
  {
    title: "Product",
    links: [
      ["For individuals", "/#individuals"],
      ["For lenders", "/#lenders"],
      ["Supported banks", "/#sources"],
      ["Pricing", "/#pricing"],
    ],
  },
  {
    title: "Trust",
    links: [
      ["Security", "/#trust"],
      ["Privacy Policy", "/privacy"],
      ["Terms of Service", "/terms"],
      ["Data protection", "/privacy"],
    ],
  },
  {
    title: "Company",
    links: [
      ["About", "/about"],
      ["Blog", "/blog"],
      ["Contact", "/contact"],
      ["Careers", "/contact"],
    ],
  },
] as const;

/** The Scanwick mark as drawn throughout the prototype. */
export function Mark({ size = 26, tone = "dark" }: { size?: number; tone?: "dark" | "light" }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: size / 4.3,
        background: tone === "dark" ? "var(--g800)" : "var(--g300)",
        color: tone === "dark" ? "#fff" : "var(--g900)",
        display: "grid",
        placeItems: "center",
        fontWeight: 800,
        fontSize: size / 2,
        flex: `0 0 ${size}px`,
      }}
    >
      S
    </div>
  );
}

function SiteLink({ href, children, style }: { href: string; children: ReactNode; style?: React.CSSProperties }) {
  const base = { textDecoration: "none", color: "inherit", ...style };
  // An in-page anchor on the landing page ("/#pricing") has to stay an <a>
  // so the browser handles the hash; everything else is a real route.
  if (href.startsWith("/#") || href.startsWith("#")) {
    return (
      <a href={href} style={base}>
        {children}
      </a>
    );
  }
  return (
    <Link to={href} style={base}>
      {children}
    </Link>
  );
}

/**
 * Both bands carry their own `.sw` scope so they can be dropped into a page
 * that has not been converted yet and still render in the prototype's
 * design system.
 */
export function Header() {
  const { status } = useAuth();
  const signedIn = status === "authenticated";
  const [open, setOpen] = useState(false);

  return (
    <div className="sw">
    <header
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "14px 32px",
        borderBottom: "1px solid var(--line)",
        background: "#fff",
        gap: 16,
        position: "relative",
        zIndex: 20,
      }}
    >
      <Link to="/" style={{ display: "flex", gap: 10, alignItems: "center", textDecoration: "none", color: "inherit" }}>
        <Mark />
        <b style={{ fontSize: 15, letterSpacing: "-.3px" }}>Scanwick</b>
      </Link>

      <button
        type="button"
        className="lp-burger btn gho sm"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={open ? "Close menu" : "Open menu"}
      >
        Menu
      </button>

      <div className={`lp-nav${open ? " open" : ""}`}>
        <div className="lp-navlinks">
          {navLinks.map(([label, href]) => (
            <SiteLink key={label} href={href} style={{ fontSize: 12.5, color: "var(--ink2)" }}>
              {label}
            </SiteLink>
          ))}
        </div>
        {signedIn ? (
          <>
            <Link to="/upload" className="btn gho sm">
              Upload a statement
            </Link>
            <Link to="/dashboard" className="btn sm">
              Go to my money
            </Link>
          </>
        ) : (
          <>
            <Link to="/login" className="btn gho sm">
              Sign in
            </Link>
            <Link to="/register" className="btn sm">
              Get started
            </Link>
          </>
        )}
      </div>
    </header>
    </div>
  );
}

export function Footer() {
  return (
    <div className="sw">
    <footer style={{ padding: "30px 32px", background: "#00190B", color: "#8FB09E" }}>
      <div className="row r4" style={{ gap: 26 }}>
        <div>
          <div style={{ display: "flex", gap: 9, alignItems: "center", marginBottom: 11 }}>
            <Mark size={22} tone="light" />
            <b style={{ color: "#fff", fontSize: 13 }}>Scanwick</b>
          </div>
          <div style={{ fontSize: 11.5, lineHeight: 1.7 }}>
            Scanwick LTD · RC 9458339
            <br />
            26 Heritage Crescent, Off Plus Eze Estate
            <br />
            Aboru, Iyana Ipaja, Lagos State, Nigeria
          </div>
        </div>

        {footerColumns.map((column) => (
          <div key={column.title} style={{ fontSize: 11.5, lineHeight: 2 }}>
            <b style={{ color: "#fff", display: "block", marginBottom: 6 }}>{column.title}</b>
            {column.links.map(([label, href]) => (
              <div key={label}>
                <SiteLink href={href}>{label}</SiteLink>
              </div>
            ))}
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: 24,
          paddingTop: 16,
          borderTop: "1px solid rgba(255,255,255,.08)",
          fontSize: 11,
          display: "flex",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 10,
        }}
      >
        <span>© 2026 Scanwick LTD. All rights reserved.</span>
        <span>Data protection enquiries · dpo@scanwick.com</span>
      </div>
    </footer>
    </div>
  );
}

export type ThemeName = "dark" | "light";

/**
 * Retained for the public pages that have not been converted yet and still
 * read a theme. The prototype specifies a single light palette, so every
 * converted screen renders that and ignores this.
 */
export function useScanwickChrome() {
  const [theme, setTheme] = useState<ThemeName>(
    () => (localStorage.getItem("scanwick-theme") as ThemeName | null) ?? "light",
  );

  const toggleTheme = () => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      localStorage.setItem("scanwick-theme", next);
      return next;
    });
  };

  return { theme, toggleTheme };
}
