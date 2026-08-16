export type WarningSeverity = "critical" | "warning";

export interface WarningItem {
  severity: WarningSeverity;
  field: string;
  description: string;
  fix: string;
}

const severityLabel: Record<WarningSeverity, string> = {
  critical: "Critical",
  warning: "Warning",
};

export function WarningsList({
  items,
  onFix,
}: {
  items: WarningItem[];
  onFix?: () => void;
}) {
  if (items.length === 0) return null;

  return (
    <div className="dqr-warnings">
      <h2 className="dqr-warnings-title">Warnings</h2>

      <div className="dqr-warnings-list">
        {items.map((item, index) => (
          <div className="dqr-warning-card" key={`${item.field}-${index}`}>
            <div className="dqr-warning-head">
              <span className={`dqr-warning-badge dqr-warning-badge-${item.severity}`}>
                {severityLabel[item.severity]}
              </span>
              <strong>{item.field}</strong>
            </div>
            <p className="dqr-warning-desc">{item.description}</p>
            {onFix ? (
              <button
                type="button"
                className="dqr-warning-fix-btn"
                onClick={onFix}
              >
                Fix &rarr; {item.fix}
              </button>
            ) : (
              <p className="dqr-warning-fix">Fix &rarr; {item.fix}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
