export function MetricPreview({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="recon-preview">
      <span className="recon-preview-label">{label}</span>
      <strong className="recon-preview-value">{value}</strong>
      <span className="recon-preview-hint">{hint}</span>
    </div>
  );
}
