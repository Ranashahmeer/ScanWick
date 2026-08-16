import {
  Activity,
  Award,
  BarChart3,
  BookOpen,
  Calendar,
  FileText,
  Lock,
  PieChart,
  ShieldCheck,
  TrendingUp,
  Wallet,
} from "lucide-react";

export interface SidebarItem {
  id: string;
  label: string;
  locked?: boolean;
}

export interface SidebarGroup {
  title?: string;
  items: SidebarItem[];
}

const sectionIcons: Record<string, typeof BarChart3> = {
  "financial-summary": PieChart,
  "income-stability": TrendingUp,
  "avg-monthly-balance": Wallet,
  "cashflow": Activity,
  "fraud-risk": ShieldCheck,
  "loan-readiness": Award,
  "90-day-forecast": Calendar,
  "lender-brief": FileText,
  "health-playbook": BookOpen,
};

export function IntelligenceSidebar({
  title,
  groups,
  open,
  activeSection,
  onSelect,
}: {
  title: string;
  groups: SidebarGroup[];
  open: boolean;
  activeSection: string;
  onSelect: (section: string) => void;
}) {
  return (
    <aside className={`fi-sidebar ${open ? "" : "fi-sidebar-collapsed"}`} aria-hidden={!open}>
      <div className="fi-sidebar-inner">
        <div className="fi-sidebar-head">
          <span className="fi-sidebar-title">{title}</span>
        </div>

        <nav aria-label={`${title} sections`}>
          {groups.map((group, index) => (
            <div className="fi-nav-group" key={index}>
              {group.title ? (
                <div
                  style={{
                    padding: "10px 14px 4px",
                    fontSize: "10px",
                    letterSpacing: "0.8px",
                    textTransform: "uppercase",
                    color: "#6E9A81",
                    fontWeight: 700,
                  }}
                >
                  {group.title}
                </div>
              ) : null}
              {group.items.map((item) => {
                const IconComponent = sectionIcons[item.id] || BarChart3;
                const isActive = activeSection === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`fi-nav-item ${isActive ? "fi-nav-item-active" : ""} ${item.locked ? "fi-nav-item-locked" : ""}`}
                    onClick={() => onSelect(item.id)}
                    aria-current={isActive ? "page" : undefined}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      width: "100%",
                      textAlign: "left",
                    }}
                  >
                    <IconComponent size={14} style={{ opacity: isActive ? 1 : 0.7, flexShrink: 0 }} />
                    <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {item.label}
                    </span>
                    {item.locked ? <Lock size={11} strokeWidth={2.4} className="fi-nav-item-lock" /> : null}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
      </div>
    </aside>
  );
}
