export interface ReconciliationSourceItem {
  label: string;
  value: string;
}

export function SourceSummary({
  title,
  subtitle,
  items,
}: {
  title: string;
  subtitle: string;
  items: ReconciliationSourceItem[];
}) {
  return (
    <div className="recon-detail">
      <h2 className="recon-detail-title">{title}</h2>
      <p className="recon-detail-subtitle">{subtitle}</p>

      <div className="recon-source">
        {items.map((item) => (
          <p className="recon-source-row" key={item.label}>
            <strong>{item.label}</strong> {item.value}
          </p>
        ))}
      </div>
    </div>
  );
}
