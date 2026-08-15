export type CheckStatus = "pass" | "fail" | "warning";

export interface StatementCheckItem {
  label: string;
  status: CheckStatus;
  /** Overrides the default status label, e.g. "3 flagged". */
  badgeLabel?: string;
}

const statusLabel: Record<CheckStatus, string> = {
  pass: "Pass",
  fail: "Flag",
  warning: "Warning",
};

export function StatementChecks({ items }: { items: StatementCheckItem[] }) {
  return (
    <div className="dqr-checks">
      <h2 className="dqr-checks-title">Statement checks</h2>

      <div className="dqr-checks-list">
        {items.map((item) => (
          <div className="dqr-check-row" key={item.label}>
            <span>{item.label}</span>
            <span className={`dqr-check-badge dqr-check-badge-${item.status}`}>
              {item.badgeLabel ?? statusLabel[item.status]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
