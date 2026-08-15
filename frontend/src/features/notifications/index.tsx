import { CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { useScanwickChrome } from "@/features/landing/chrome";
import { AppTopbar } from "@/features/upload/components/topbar";

type Module = "finance" | "commerce";
type Severity = "critical" | "warning" | "info";
type SectionId = "alerts" | "recommendations" | "team" | "dataQuality";

interface NotificationItem {
  id: string;
  section: SectionId;
  module: Module;
  severity: Severity;
  title: string;
  description: string;
  time: string;
}

const moduleFilters: { id: "all" | Module; label: string }[] = [
  { id: "all", label: "All" },
  { id: "finance", label: "Finance" },
  { id: "commerce", label: "Commerce" },
];

const severityFilters: { id: Severity; label: string }[] = [
  { id: "critical", label: "Critical" },
  { id: "warning", label: "Warning" },
  { id: "info", label: "Info" },
];

const sectionTitles: Record<SectionId, string> = {
  alerts: "Active alerts",
  recommendations: "AI recommendations",
  team: "Team activity",
  dataQuality: "Data quality warnings",
};

const sectionOrder: SectionId[] = ["alerts", "recommendations", "team", "dataQuality"];

const initialNotifications: NotificationItem[] = [
  {
    id: "stockout-lmp014",
    section: "alerts",
    module: "commerce",
    severity: "critical",
    title: "Stockout alert — LMP-014",
    description: "Rattan Pendant Lamp - 7 days of cover left",
    time: "2h ago",
  },
  {
    id: "stale-commerce-sync",
    section: "alerts",
    module: "commerce",
    severity: "warning",
    title: "Stale data",
    description: "Commerce sync 31h ago — reconnect to refresh",
    time: "today",
  },
  {
    id: "reorder-lmp014",
    section: "recommendations",
    module: "commerce",
    severity: "info",
    title: "Reorder LMP-014 before 5 Jul",
    description: "₦1.24M at stake · 92% confidence",
    time: "today",
  },
  {
    id: "role-changed-tunde",
    section: "team",
    module: "commerce",
    severity: "info",
    title: "Role changed",
    description: "Tunde set to Warehouse Manager (Commerce)",
    time: "yesterday",
  },
  {
    id: "invite-accepted",
    section: "team",
    module: "finance",
    severity: "info",
    title: "Invite accepted",
    description: "accountant@lumio.ng joined as Accountant",
    time: "2d ago",
  },
  {
    id: "date-gap-gtbank",
    section: "dataQuality",
    module: "finance",
    severity: "warning",
    title: "Date gap in GTBank statement",
    description: "2–7 Apr - affects Income Stability",
    time: "today",
  },
];

export function NotificationCenterPage() {
  const { theme, toggleTheme } = useScanwickChrome();
  const [notifications, setNotifications] = useState(initialNotifications);
  const [moduleFilter, setModuleFilter] = useState<"all" | Module>("all");
  const [severityFilter, setSeverityFilter] = useState<Set<Severity>>(new Set());

  const toggleSeverity = (severity: Severity) => {
    setSeverityFilter((current) => {
      const next = new Set(current);
      if (next.has(severity)) next.delete(severity);
      else next.add(severity);
      return next;
    });
  };

  const visible = notifications.filter(
    (item) =>
      (moduleFilter === "all" || item.module === moduleFilter) &&
      (severityFilter.size === 0 || severityFilter.has(item.severity)),
  );

  const sections = sectionOrder
    .map((id) => ({
      id,
      title: sectionTitles[id],
      items: visible.filter((item) => item.section === id),
    }))
    .filter((section) => section.items.length > 0);

  return (
    <main className={`scanwick-page upload-page ${theme === "light" ? "theme-light" : ""}`}>
      <AppTopbar theme={theme} onToggleTheme={toggleTheme} />

      <section className="upload-main">
        <div className="notif-inner">
          <div className="notif-heading">
            <div>
              <h1>Notification Center</h1>
              <p>Alerts, recommendations, and team activity across every module.</p>
            </div>
            <button
              type="button"
              className="notif-mark-read"
              onClick={() => setNotifications([])}
              disabled={notifications.length === 0}
            >
              Mark all read
            </button>
          </div>

          <div className="notif-filters">
            <div className="notif-filter-group" role="radiogroup" aria-label="Module">
              {moduleFilters.map((filter) => (
                <button
                  key={filter.id}
                  type="button"
                  role="radio"
                  aria-checked={moduleFilter === filter.id}
                  className={`upload-pill ${moduleFilter === filter.id ? "is-active" : ""}`}
                  onClick={() => setModuleFilter(filter.id)}
                >
                  {filter.label}
                </button>
              ))}
            </div>

            <span className="notif-filter-label">Severity</span>
            <div className="notif-filter-group" role="group" aria-label="Severity">
              {severityFilters.map((filter) => (
                <button
                  key={filter.id}
                  type="button"
                  aria-pressed={severityFilter.has(filter.id)}
                  className={`notif-severity-pill notif-severity-pill-${filter.id} ${
                    severityFilter.has(filter.id) ? "is-active" : ""
                  }`}
                  onClick={() => toggleSeverity(filter.id)}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>

          {sections.length ? (
            sections.map((section) => (
              <div className="notif-section" key={section.id}>
                <h2>{section.title}</h2>
                <div className="notif-list">
                  {section.items.map((item) => (
                    <div className="notif-row" key={item.id}>
                      <span className={`notif-dot notif-dot-${item.severity}`} />
                      <div className="notif-row-body">
                        <strong>{item.title}</strong>
                        <p>{item.description}</p>
                      </div>
                      <span className="notif-time">{item.time}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))
          ) : (
            <div className="notif-empty">
              <CheckCircle2 size={28} strokeWidth={2} />
              <strong>You're all caught up</strong>
              <p>No active alerts or pending recommendations.</p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
