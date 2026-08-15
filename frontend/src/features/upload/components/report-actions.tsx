export function ReportActions({
  onProceed,
  onFixReupload,
  primaryLabel = "Proceed to dashboard",
  primaryDisabled = false,
}: {
  onProceed: () => void;
  onFixReupload: () => void;
  primaryLabel?: string;
  primaryDisabled?: boolean;
}) {
  return (
    <div className="dqr-actions">
      <button
        type="button"
        className="dqr-action-primary"
        onClick={onProceed}
        disabled={primaryDisabled}
        aria-disabled={primaryDisabled}
      >
        {primaryLabel}
      </button>
      <button type="button" className="dqr-action-secondary" onClick={onFixReupload}>
        Fix &amp; re-upload
      </button>
    </div>
  );
}
