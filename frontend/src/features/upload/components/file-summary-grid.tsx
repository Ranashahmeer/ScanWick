export interface FileSummaryItem {
  label: string;
  value: string;
}

export function FileSummaryGrid({ items }: { items: FileSummaryItem[] }) {
  return (
    <div className="dqr-summary">
      {items.map((item) => (
        <div className="dqr-summary-item" key={item.label}>
          <span className="dqr-summary-label">{item.label}</span>
          <span className="dqr-summary-value">{item.value}</span>
        </div>
      ))}
    </div>
  );
}
