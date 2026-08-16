export function ReportActions({
  onProceed,
  onFixReupload,
  primaryLabel = "Proceed to dashboard",
  isFailed = false,
}: {
  onProceed: () => void;
  onFixReupload: () => void;
  primaryLabel?: string;
  isFailed?: boolean;
}) {
  return (
    <div className="dqr-actions">
      {isFailed ? (
        <>
          <button
            type="button"
            className="dqr-action-primary dqr-action-fix"
            onClick={onFixReupload}
          >
            {primaryLabel || "Resolve errors (Fix & re-upload)"}
          </button>
          <button
            type="button"
            className="dqr-action-secondary"
            onClick={onProceed}
          >
            Proceed to dashboard anyway &rarr;
          </button>
        </>
      ) : (
        <>
          <button
            type="button"
            className="dqr-action-primary"
            onClick={onProceed}
          >
            {primaryLabel}
          </button>
          <button
            type="button"
            className="dqr-action-secondary"
            onClick={onFixReupload}
          >
            Fix &amp; re-upload
          </button>
        </>
      )}
    </div>
  );
}
