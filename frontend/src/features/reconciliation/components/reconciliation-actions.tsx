export function ReconciliationActions({
  onDownload,
  onClose,
}: {
  onDownload: () => void;
  onClose: () => void;
}) {
  return (
    <div className="dqr-actions">
      <button type="button" className="dqr-action-primary" onClick={onDownload}>
        Download CSV
      </button>
      <button type="button" className="dqr-action-secondary" onClick={onClose}>
        Close
      </button>
    </div>
  );
}
