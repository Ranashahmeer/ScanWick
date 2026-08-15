import { Lock } from "lucide-react";

export interface SidebarItem {
  id: string;
  label: string;
  // Set by each vertical's index.tsx from the plan permissions matrix —
  // the item stays clickable (selecting it shows PlanUpgradeLockedPage,
  // see shared.tsx), this is just an earlier visual signal than a dead end.
  locked?: boolean;
}

export interface SidebarGroup {
  items: SidebarItem[];
}

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
              {group.items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`fi-nav-item ${activeSection === item.id ? "fi-nav-item-active" : ""} ${item.locked ? "fi-nav-item-locked" : ""}`}
                  onClick={() => onSelect(item.id)}
                  aria-current={activeSection === item.id ? "page" : undefined}
                >
                  {item.label}
                  {item.locked ? <Lock size={11} strokeWidth={2.4} className="fi-nav-item-lock" /> : null}
                </button>
              ))}
            </div>
          ))}
        </nav>
      </div>
    </aside>
  );
}
