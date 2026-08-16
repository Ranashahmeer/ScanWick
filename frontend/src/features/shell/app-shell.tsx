/**
 * The authenticated application shell — prototype `.side` sidebar plus the
 * screen frame every signed-in page renders into.
 *
 * The prototype draws its own navigator down the left in Scanwick's dark
 * green; that is the product's sidebar treatment, so it is reproduced here
 * exactly (268px, --g900 ground, grouped labels at 10/700/.9 uppercase, the
 * mono screen-number rail, the --g300 active border).
 *
 * Below 900px it becomes an off-canvas drawer behind a topbar burger, since
 * the prototype states the individual surface is met on a phone.
 */

import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "@tanstack/react-router";

import { useAuth } from "@/hooks/use-auth";
import { groupsForSurface, surfaceFor, type NavItem } from "./nav";

function isCurrent(item: NavItem, pathname: string, search: Record<string, unknown>): boolean {
  if (item.to !== pathname) return false;
  if (!item.search) {
    // The bare route is current only when no sub-view is selected.
    return !Object.keys(search).some((k) => k === "view" || k === "tab");
  }
  return Object.entries(item.search).every(([k, v]) => search[k] === v);
}

export function AppShell({
  children,
  /** Page-level title, rendered by the page itself via <ScreenHead>. */
}: {
  children: ReactNode;
}) {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const surface = surfaceFor(user?.roles);
  const groups = groupsForSurface(surface);
  const search = (location.search ?? {}) as Record<string, unknown>;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const initials =
    [user?.first_name?.[0], user?.last_name?.[0]].filter(Boolean).join("").toUpperCase() ||
    user?.email?.[0]?.toUpperCase() ||
    "·";

  return (
    <div className="sw">
      <div className="topbar">
        <button
          type="button"
          className="burger"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
        >
          ☰
        </button>
        <div className="brand">
          <div className="mk">S</div>
          <b style={{ fontSize: 14 }}>Scanwick</b>
        </div>
        <Link
          to="/account"
          style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: "var(--g700)",
            color: "#fff",
            display: "grid",
            placeItems: "center",
            fontSize: 11,
            fontWeight: 700,
            textDecoration: "none",
          }}
          aria-label="Your account"
        >
          {initials}
        </Link>
      </div>

      <div className="sw-wrap">
        {open ? <div className="sw-scrim" onClick={() => setOpen(false)} /> : null}

        <nav className={`side${open ? " open" : ""}`} aria-label="Application navigation">
          <div className="brand">
            <div className="mk">S</div>
            <div>
              <b>Scanwick</b>
              <span>{surface === "institution" ? "Institution" : "Personal"}</span>
            </div>
          </div>

          {groups.map((group) => (
            <div key={group.title}>
              <div className="grp">{group.title}</div>
              {group.items.map((item) => (
                <button
                  key={`${item.to}-${item.n}`}
                  type="button"
                  className={`navitem${isCurrent(item, location.pathname, search) ? " on" : ""}`}
                  aria-current={isCurrent(item, location.pathname, search) ? "page" : undefined}
                  onClick={() => {
                    // Closed here rather than in an effect on the location:
                    // navigation is the thing that should dismiss the
                    // drawer, and this is where it happens.
                    setOpen(false);
                    navigate({ to: item.to, search: (item.search ?? {}) as never });
                  }}
                >
                  <i>{item.n}</i>
                  {item.label}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <main className="main">{children}</main>
      </div>
    </div>
  );
}

/**
 * A screen inside the shell. Wraps content in the prototype's `.scr` frame
 * so padding and max width are identical on every page.
 */
export function Screen({ children }: { children: ReactNode }) {
  return <div className="scr">{children}</div>;
}

/** A public (signed-out) page in the prototype's visual language. */
export function PublicShell({ children }: { children: ReactNode }) {
  return <div className="sw">{children}</div>;
}
