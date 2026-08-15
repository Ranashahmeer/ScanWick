import { useState } from "react";
import { getRouteApi } from "@tanstack/react-router";
import { useScanwickChrome } from "@/features/landing/chrome";
import { AppTopbar } from "@/features/upload/components/topbar";
import { TeamPermissions } from "./team-permissions";
import { ContextualMarkers } from "./contextual-markers";
import { AccountBilling } from "./account-billing";
import { WorkspaceSettings } from "./workspace-settings";

type Section = "billing" | "team" | "markers" | "settings";

const sections: { id: Section; label: string }[] = [
  { id: "billing", label: "Account & Billing" },
  { id: "team", label: "Team & Permissions" },
  { id: "markers", label: "Contextual Markers" },
  { id: "settings", label: "Settings" },
];

const accountRoute = getRouteApi("/_app/account/");

const sectionHeading: Record<Section, { title: string; description: string }> = {
  billing: {
    title: "Account & Billing",
    description: "Your profile, security, subscription, and data — owner-managed.",
  },
  team: {
    title: "Team & Permissions",
    description: "Assign a role per module. Each member sees only the navigation their role allows.",
  },
  markers: {
    title: "Contextual Markers",
    description: "Tag unusual periods so the AI doesn't learn from them.",
  },
  settings: {
    title: "Settings",
    description: "Workspace configuration. Visible to Store Owner / CFO only.",
  },
};

export function AccountSettingsPage() {
  const { theme, toggleTheme } = useScanwickChrome();
  const { tab, upgrade } = accountRoute.useSearch();
  const [section, setSection] = useState<Section>(tab ?? "billing");
  const heading = sectionHeading[section];

  return (
    <main className={`scanwick-page upload-page ${theme === "light" ? "theme-light" : ""}`}>
      <AppTopbar theme={theme} onToggleTheme={toggleTheme} />

      <section className="upload-main">
        <div className="acct-inner">
          <div className="upload-heading">
            <h1>{heading.title}</h1>
            <p>{heading.description}</p>
          </div>

          <div className="upload-tabs acct-section-nav" role="tablist" aria-label="Account settings section">
            {sections.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={section === item.id}
                className={`upload-tab ${section === item.id ? "is-active" : ""}`}
                onClick={() => setSection(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="acct-section-content">
            {section === "billing" ? <AccountBilling initialUpgradeTier={upgrade} /> : null}
            {section === "team" ? <TeamPermissions /> : null}
            {section === "markers" ? <ContextualMarkers /> : null}
            {section === "settings" ? <WorkspaceSettings /> : null}
          </div>
        </div>
      </section>
    </main>
  );
}
