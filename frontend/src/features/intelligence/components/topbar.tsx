import {
  Bell,
  Calendar,
  Menu,
  Moon,
  RefreshCw,
  Settings,
  Sun,
  X,
} from "lucide-react";
import { Link } from "@tanstack/react-router";
import scanwickLogo from "@/assets/Logos/Full Scanwick Logo Light Green.svg";

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

        {/* Which dashboard is open is determined by the uploaded dataset's
            type, not a manual switcher -- this is now a plain label, not a
            dropdown. */}
        <span className="fi-topbar-crumb fi-topbar-crumb-static">{moduleLabel}</span>

        <div className="fi-topbar-spacer" />

        <span className="fi-date-badge">
          <Calendar size={13} strokeWidth={2.3} />
          {dateRangeLabel}
        </span>

        <div className="fi-topbar-actions">
          <button type="button" className="upload-icon-btn" aria-label="Refresh data">
            <RefreshCw size={15} strokeWidth={2.3} />
          </button>
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
