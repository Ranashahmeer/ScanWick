import type { ReactNode } from "react";
import { ArrowDown, ArrowUp, Lock, Minus } from "lucide-react";

export function PageHead({
  module,
  breadcrumb,
  title,
  description,
}: {
  module: string;
  breadcrumb: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="fi-page-head">
      <p className="fi-breadcrumb">
        {module} <strong>{breadcrumb}</strong>
      </p>
      <h1>{title}</h1>
      {description ? <p>{description}</p> : null}
    </div>
  );
}

export function Card({
  title,
  hint,
  children,
  className = "",
}: {
  title?: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`fi-card ${className}`}>
      {title ? (
        <div className="fi-card-head">
          <h2 className="fi-card-title">{title}</h2>
          {hint ? <span className="fi-card-hint">{hint}</span> : null}
        </div>
      ) : null}
      {children}
    </div>
  );
}

export interface StatTileData {
  label: string;
  value: string;
  delta?: { direction: "up" | "down"; label: string };
  onReconcile?: () => void;
}

export function StatTile({ label, value, delta, onReconcile }: StatTileData) {
  return (
    <div className="fi-card fi-stat-tile">
      <span className="fi-stat-label">{label}</span>
      <span className="fi-stat-value">{value}</span>
      {delta ? (
        <span className={`fi-stat-delta ${delta.direction === "up" ? "fi-stat-delta-up" : "fi-stat-delta-down"}`}>
          {delta.direction === "up" ? (
            <ArrowUp size={11} strokeWidth={2.6} />
          ) : (
            <ArrowDown size={11} strokeWidth={2.6} />
          )}
          {delta.label}
        </span>
      ) : null}
      {onReconcile ? (
        <button type="button" className="fi-stat-link" onClick={onReconcile}>
          &#8618; reconciliation
        </button>
      ) : null}
    </div>
  );
}

export function Legend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <div className="fi-legend">
      {items.map((item) => (
        <span className="fi-legend-item" key={item.label}>
          <span className="fi-legend-dot" style={{ background: item.color }} />
          {item.label}
        </span>
      ))}
    </div>
  );
}

export function BarList({
  items,
}: {
  items: { label: string; value: string; percent: number }[];
}) {
  return (
    <div className="fi-bar-list">
      {items.map((item) => (
        <div className="fi-bar-row" key={item.label}>
          <div className="fi-bar-row-head">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
          <div className="fi-bar-track">
            <div className="fi-bar-fill" style={{ width: `${item.percent}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ItemList({
  items,
}: {
  items: { name: string; value: string; pct: string }[];
}) {
  return (
    <div className="fi-item-list">
      {items.map((item) => (
        <div className="fi-item-row" key={item.name}>
          <span className="fi-item-name">{item.name}</span>
          <span className="fi-item-meta">
            <span className="fi-item-value">{item.value}</span>
            <span className="fi-item-pct">{item.pct}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

export function ProgressBar({ percent, label }: { percent: number; label: string }) {
  return (
    <>
      <div className="fi-progress-track">
        <div className="fi-progress-fill" style={{ width: `${percent}%` }} />
      </div>
      <p className="fi-progress-label">{label}</p>
    </>
  );
}

export function LockedOverlay({
  title,
  onAction,
  actionLabel = "Upgrade →",
  children,
}: {
  title?: string;
  onAction?: () => void;
  actionLabel?: string;
  children: ReactNode;
}) {
  return (
    <div className="fi-card">
      {title ? (
        <div className="fi-card-head">
          <h2 className="fi-card-title">{title}</h2>
        </div>
      ) : null}
      <div className="fi-locked">
        <div className="fi-locked-content" aria-hidden="true">
          {children}
        </div>
        <div className="fi-locked-overlay">
          <span className="fi-premium-badge">
            <Lock size={10} strokeWidth={2.6} />
            Premium
          </span>
          <button type="button" onClick={onAction}>
            {actionLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

export function LockedPageState({
  title,
  description,
  note,
  pillLabel,
  actionLabel,
  onAction,
}: {
  title: string;
  description: string;
  note?: string;
  pillLabel?: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="fi-locked-page">
      <span className="fi-locked-page-icon">
        <Lock size={18} strokeWidth={2.2} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {note ? <p className="fi-locked-page-note">{note}</p> : null}
      {pillLabel ? <span className="fi-locked-page-pill">{pillLabel}</span> : null}
      {actionLabel ? (
        <button type="button" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}

// Inline banner for a page that IS rendering (unlike LockedPageState,
// which replaces a page entirely) but with a plan-tier-truncated response —
// e.g. Free seeing only the top profit leak. `detail` is the exact phrase
// from plan_permissions.py (via the response's meta.plan_access.detail),
// so the copy here always matches what the matrix file actually says.
export function LimitedAccessBanner({ detail, onAction }: { detail: string; onAction?: () => void }) {
  return (
    <div className="fi-limited-banner">
      <Lock size={13} strokeWidth={2.4} />
      <span>
        You're seeing a limited view on your current plan: <strong>{detail}</strong>.
      </span>
      <button type="button" onClick={onAction}>
        Upgrade for the full view →
      </button>
    </div>
  );
}

// Replaces a whole page's content when the caller's plan doesn't include
// it at all (access level NONE) — distinct from LockedPageState's existing
// uses (which are all about missing/insufficient *data*, not plan tier),
// so the copy here is unambiguously about upgrading, not uploading more
// data. Thin wrapper around LockedPageState rather than a full fork, since
// its props already cover this shape exactly.
export function PlanUpgradeLockedPage({ label }: { label: string }) {
  return (
    <LockedPageState
      title={`${label} is a paid-plan feature`}
      description="Upgrade your plan to unlock this section."
      actionLabel="Upgrade plan →"
      onAction={() => {
        window.location.href = "/account?tab=billing";
      }}
    />
  );
}

export type BadgeTone = "neutral" | "success" | "warning" | "danger";

export function Badge({ tone = "neutral", children }: { tone?: BadgeTone; children: ReactNode }) {
  return <span className={`fi-badge fi-badge-${tone}`}>{children}</span>;
}

export function TrendBadge({ direction, label }: { direction: "up" | "down" | "flat"; label: string }) {
  const Icon = direction === "up" ? ArrowUp : direction === "down" ? ArrowDown : Minus;
  const tone = direction === "up" ? "fi-trend-up" : direction === "down" ? "fi-trend-down" : "fi-trend-flat";
  return (
    <span className={`fi-trend ${tone}`}>
      <Icon size={11} strokeWidth={2.6} />
      {label}
    </span>
  );
}

export function RepAvatar({ name, color = "#7fc7a3" }: { name: string; color?: string }) {
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <span className="fi-avatar" style={{ color, background: `${color}26`, borderColor: `${color}55` }}>
      {initials}
    </span>
  );
}

export interface TableColumn {
  key: string;
  label: string;
  align?: "left" | "right";
  width?: string;
}

export function Table({
  columns,
  rows,
  rowKey,
  rowTone,
}: {
  columns: TableColumn[];
  rows: Record<string, ReactNode>[];
  rowKey: (row: Record<string, ReactNode>, index: number) => string;
  rowTone?: (row: Record<string, ReactNode>, index: number) => BadgeTone | undefined;
}) {
  const template = columns.map((c) => c.width ?? "1fr").join(" ");

  return (
    <div className="fi-table">
      <div className="fi-table-head" style={{ gridTemplateColumns: template }}>
        {columns.map((col) => (
          <span key={col.key} className={col.align === "right" ? "fi-table-al-r" : ""}>
            {col.label}
          </span>
        ))}
      </div>
      <div>
        {rows.map((row, index) => {
          const tone = rowTone?.(row, index);
          return (
            <div
              className={`fi-table-row ${tone ? `fi-table-row-${tone}` : ""}`}
              style={{ gridTemplateColumns: template }}
              key={rowKey(row, index)}
            >
              {columns.map((col) => (
                <span key={col.key} className={col.align === "right" ? "fi-table-al-r" : ""}>
                  {row[col.key]}
                </span>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function QuotaBullet({
  label,
  percent,
  tone,
}: {
  label: string;
  percent: number;
  tone: "success" | "warning" | "danger";
}) {
  const clamped = Math.min(percent, 130);
  return (
    <div className="fi-bullet-row">
      <span className="fi-bullet-label">{label}</span>
      <div className="fi-bullet-track">
        <div className="fi-bullet-band fi-bullet-band-low" />
        <div className="fi-bullet-band fi-bullet-band-mid" />
        <div className="fi-bullet-band fi-bullet-band-high" />
        <div className={`fi-bullet-fill fi-bullet-fill-${tone}`} style={{ width: `${clamped}%` }} />
        <div className="fi-bullet-tick" style={{ left: "100%" }} />
        <span className="fi-bullet-value" style={{ left: `${clamped}%` }}>
          {percent}%
        </span>
      </div>
    </div>
  );
}

export function LikelihoodDot({ percent }: { percent: number }) {
  const tone = percent > 70 ? "#7fc7a3" : percent >= 50 ? "#f0b060" : "#f06060";
  return (
    <span className="fi-likelihood">
      <span className="fi-likelihood-dot" style={{ background: tone }} />
      {percent}%
    </span>
  );
}
