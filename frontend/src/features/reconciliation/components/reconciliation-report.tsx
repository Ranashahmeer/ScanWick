import { useEffect } from "react";
import { AppTopbar } from "@/features/upload/components/topbar";
import { MetricPreview } from "./metric-preview";
import { SourceSummary } from "./source-summary";
import { ExcludedRecordsTable } from "./excluded-records-table";
import { ReconciliationTotals } from "./reconciliation-totals";
import { ReconciliationActions } from "./reconciliation-actions";
import { useReconciliationReport, type ReconciliationReportData } from "../reconciliation-api";

function downloadReconciliationCsv(data: ReconciliationReportData) {
  const rows = [
    ["Field", "Value"],
    ["Analyzer", data.analyzer_type],
    ["Date range start", data.date_range_start ?? ""],
    ["Date range end", data.date_range_end ?? ""],
    ["Base currency", data.base_currency ?? ""],
    ["Records analyzed", String(data.records_analyzed ?? "")],
    ["Records excluded", String(data.records_excluded ?? "")],
    [],
    ["Reason", "Count", "Value"],
    ...data.exclusion_detail.map((item) => [item.reason, String(item.count), item.value]),
  ];
  const csv = rows.map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(",")).join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `reconciliation-${data.id}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export function ReconciliationReport({
  theme,
  onToggleTheme,
  analysisRunId,
  onClose,
}: {
  theme: "dark" | "light";
  onToggleTheme: () => void;
  analysisRunId: string;
  onClose: () => void;
}) {
  const query = useReconciliationReport(analysisRunId);
  const data = query.data;

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="recon-overlay" role="presentation" onClick={onClose}>
      <div
        className={`scanwick-page recon-panel ${theme === "light" ? "theme-light" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label="Reconciliation report"
        onClick={(event) => event.stopPropagation()}
      >
        <AppTopbar theme={theme} onToggleTheme={onToggleTheme} />

        <div className="recon-scroll">
          <div className="recon-inner">
            <div className="upload-heading">
              <h1>Reconciliation Report</h1>
              <p>Every dashboard metric links back to the analysis run that produced it — this is that record.</p>
            </div>

            {!data ? (
              query.isError ? (
                <p className="fi-card-note">
                  {(query.error as { response?: { status?: number } })?.response?.status === 403
                    ? "You don't have access to this merchant's data for this vertical."
                    : "Could not load this reconciliation report."}
                </p>
              ) : (
                <p className="fi-card-note">Loading…</p>
              )
            ) : (
              <div className="recon-layout">
                <MetricPreview
                  label={`${data.analyzer_type} analysis`}
                  value={String(data.records_analyzed ?? "—")}
                  hint={data.created_at ? new Date(data.created_at).toLocaleString() : "Records analyzed"}
                />

                <div className="recon-detail-col">
                  <SourceSummary
                    title={`${data.analyzer_type} run ${data.id.slice(0, 8)}`}
                    subtitle="How this analysis run was scoped"
                    items={[
                      { label: "Date range", value: data.date_range_start && data.date_range_end ? `${data.date_range_start} – ${data.date_range_end}` : "Not scoped to a date range" },
                      { label: "Base currency", value: data.base_currency ?? "—" },
                      { label: "Exchange rate source", value: data.exchange_rate_source ?? "—" },
                      { label: "Source file", value: data.source_file_id ?? "Not linked to a specific upload" },
                    ]}
                  />

                  <ExcludedRecordsTable
                    items={data.exclusion_detail}
                    recordsExcluded={data.records_excluded ?? 0}
                  />

                  {data.disabled_features.length > 0 ? (
                    <div className="recon-detail">
                      <h2 className="recon-detail-title">Disabled features on this run</h2>
                      <div className="recon-source">
                        {data.disabled_features.map((feature) => (
                          <p className="recon-source-row" key={feature.feature_name}>
                            <strong>{feature.feature_name}</strong> {feature.reason}
                          </p>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  <ReconciliationTotals
                    totalProcessed={String(data.records_analyzed ?? "—")}
                    totalExcluded={String(data.records_excluded ?? "0")}
                    note="Records analyzed is already net of exclusions (e.g. anomalous transactions, own-account transfers) — see the breakdown above if any exist for this run."
                  />
                </div>
              </div>
            )}

            <ReconciliationActions
              onDownload={() => data && downloadReconciliationCsv(data)}
              onClose={onClose}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
