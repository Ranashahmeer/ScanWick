import {
  Bell,
  Calendar,
  LogOut,
  Menu,
  Moon,
  RefreshCw,
  Settings,
  Sun,
  User,
  X,
} from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { Link } from "@tanstack/react-router";
import scanwickLogo from "@/assets/Logos/Full Scanwick Logo Light Green.svg";
import { useAuth } from "@/hooks/use-auth";
import { logoutUser } from "@/lib/auth-tokens";

export function IntelligenceTopbar({
  theme,
  onToggleTheme,
  sidebarOpen,
  onToggleSidebar,
  dateRangeLabel,
  moduleLabel,
}: {
  theme: "dark" | "light";
  onToggleTheme: () => void;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  dateRangeLabel: string;
  moduleLabel: string;
}) {
  const isLight = theme === "light";
  const { user } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const initials = user?.first_name && user?.last_name
    ? `${user.first_name[0]}${user.last_name[0]}`.toUpperCase()
    : user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : "US";

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="fi-topbar">
      <div className="fi-topbar-inner">
        <button
          type="button"
          className="upload-icon-btn"
          onClick={onToggleSidebar}
          aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          aria-pressed={sidebarOpen}
        >
          {sidebarOpen ? <X size={15} strokeWidth={2.3} /> : <Menu size={15} strokeWidth={2.3} />}
        </button>

        <Link to="/" className="upload-logo-link" aria-label="Scanwick home">
          <img src={scanwickLogo} alt="Scanwick" className="upload-logo" />
        </Link>

        <span className="fi-topbar-crumb fi-topbar-crumb-static">{moduleLabel}</span>

        <div className="fi-topbar-spacer" />

        <span className="fi-date-badge">
          <Calendar size={13} strokeWidth={2.3} />
          {dateRangeLabel}
        </span>

        <div className="fi-topbar-actions">
          <Link to="/upload" className="upload-icon-btn" title="Upload statement" style={{ textDecoration: "none", color: "inherit" }}>
            <RefreshCw size={15} strokeWidth={2.3} />
          </Link>
          <Link to="/notifications" className="upload-icon-btn" aria-label="Notifications">
            <Bell size={15} strokeWidth={2.3} />
          </Link>
          <Link to="/account" className="upload-icon-btn" aria-label="Account settings">
            <Settings size={15} strokeWidth={2.3} />
          </Link>
          <button
            type="button"
            className="upload-icon-btn"
            onClick={onToggleTheme}
            aria-label={isLight ? "Switch to dark theme" : "Switch to light theme"}
            aria-pressed={isLight}
          >
            {isLight ? <Moon size={15} strokeWidth={2.3} /> : <Sun size={15} strokeWidth={2.3} />}
          </button>

          <div style={{ position: "relative" }} ref={dropdownRef}>
            <button
              type="button"
              className="upload-avatar"
              onClick={() => setDropdownOpen((open) => !open)}
              style={{
                border: "none",
                cursor: "pointer",
                background: "var(--sw-g700, #0a4a2a)",
                color: "#ffffff",
                fontWeight: 700,
                fontSize: 12,
              }}
              title={user?.email ?? "Account"}
            >
              {initials}
            </button>

            {dropdownOpen ? (
              <div
                style={{
                  position: "absolute",
                  right: 0,
                  top: "calc(100% + 8px)",
                  width: 220,
                  background: "var(--card, #ffffff)",
                  border: "1px solid var(--border, #dce3df)",
                  borderRadius: 10,
                  boxShadow: "0 4px 20px rgba(0,0,0,0.12)",
                  padding: "10px 0",
                  zIndex: 50,
                  color: "var(--foreground, #0e1512)",
                }}
              >
                <div style={{ padding: "6px 16px 10px", borderBottom: "1px solid var(--border, #dce3df)" }}>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>
                    {user?.first_name ? `${user.first_name} ${user.last_name || ""}` : "Scanwick User"}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--muted-foreground, #6b7a72)", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {user?.email ?? ""}
                  </div>
                </div>

                <div style={{ padding: "6px 0" }}>
                  <Link
                    to="/dashboard"
                    onClick={() => setDropdownOpen(false)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "8px 16px",
                      fontSize: 12.5,
                      color: "inherit",
                      textDecoration: "none",
                    }}
                  >
                    <User size={14} /> Dashboard
                  </Link>
                  <Link
                    to="/upload"
                    onClick={() => setDropdownOpen(false)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "8px 16px",
                      fontSize: 12.5,
                      color: "inherit",
                      textDecoration: "none",
                    }}
                  >
                    <RefreshCw size={14} /> Upload Statement
                  </Link>
                  <Link
                    to="/account"
                    onClick={() => setDropdownOpen(false)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "8px 16px",
                      fontSize: 12.5,
                      color: "inherit",
                      textDecoration: "none",
                    }}
                  >
                    <Settings size={14} /> Account & Billing
                  </Link>
                </div>

                <div style={{ borderTop: "1px solid var(--border, #dce3df)", paddingTop: 6 }}>
                  <button
                    type="button"
                    onClick={() => logoutUser()}
                    style={{
                      width: "100%",
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "8px 16px",
                      fontSize: 12.5,
                      color: "var(--sw-stop, #9b2c2c)",
                      background: "transparent",
                      border: "none",
                      cursor: "pointer",
                      fontWeight: 600,
                      textAlign: "left",
                    }}
                  >
                    <LogOut size={14} /> Sign out
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
