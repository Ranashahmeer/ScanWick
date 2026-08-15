export interface ExcludedRecordItem {
  reason: string;
  count: number;
  value: string;
}

export function ExcludedRecordsTable({
  items,
  recordsExcluded,
}: {
  items: ExcludedRecordItem[];
  recordsExcluded: number;
}) {
  if (items.length === 0) {
    if (recordsExcluded > 0) {
      return (
        <div className="recon-excluded">
          <h3 className="recon-excluded-title">Excluded records</h3>
          <p className="recon-excluded-empty-note">
            Exclusion reasons not available for this report.
          </p>
        </div>
      );
    }
    return null;
  }

  return (
    <div className="recon-excluded">
      <h3 className="recon-excluded-title">Excluded records</h3>

      <div className="recon-excluded-table">
        <div className="recon-excluded-row recon-excluded-head">
          <span>Reason</span>
          <span>Count</span>
          <span>Value</span>
        </div>

        {items.map((item, index) => (
          <div className="recon-excluded-row" key={`${item.reason}-${index}`}>
            <span>{item.reason}</span>
            <span>{item.count}</span>
            <span>{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
