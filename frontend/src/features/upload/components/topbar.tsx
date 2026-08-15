import { Bell, Moon, RefreshCw, Settings, Sun } from "lucide-react";
import { Link } from "@tanstack/react-router";
import scanwickLogo from "@/assets/Logos/Full Scanwick Logo Light Green.svg";

export function AppTopbar({
  theme,
  onToggleTheme,
  onReset,
}: {
  theme: "dark" | "light";
  onToggleTheme: () => void;
  onReset?: () => void;
}) {
  const isLight = theme === "light";

  return (
    <header className="upload-topbar">
      <div className="upload-topbar-inner">
        <Link to="/" className="upload-logo-link" aria-label="Scanwick home">
          <img src={scanwickLogo} alt="Scanwick" className="upload-logo" />
        </Link>

        <div className="upload-topbar-actions">
          {onReset ? (
            <button
              type="button"
              className="upload-icon-btn"
              onClick={onReset}
              aria-label="Start a new upload"
            >
              <RefreshCw size={15} strokeWidth={2.3} />
            </button>
          ) : null}
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
          <span className="upload-avatar" aria-label="Guest account">
            AO
          </span>
        </div>
      </div>
    </header>
  );
}
