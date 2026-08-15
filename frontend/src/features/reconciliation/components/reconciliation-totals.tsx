export function ReconciliationTotals({
  totalProcessed,
  totalExcluded,
  note,
}: {
  totalProcessed: string;
  totalExcluded: string;
  note: string;
}) {
  return (
    <>
      <div className="recon-totals">
        <p>
          <strong>Net records analyzed:</strong> {totalProcessed}
        </p>
        <p>
          <strong>Total excluded:</strong> {totalExcluded}
        </p>
      </div>

      <p className="recon-note">{note}</p>
    </>
  );
}
