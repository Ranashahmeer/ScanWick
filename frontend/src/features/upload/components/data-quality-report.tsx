import { AppTopbar } from "./topbar";
import { FileSummaryGrid, type FileSummaryItem } from "./file-summary-grid";
import { StatementChecks } from "./statement-checks";
import { MappingAppliedCard } from "./mapping-applied-summary";
import { WarningsList } from "./warnings-list";
import { DisabledFeaturesList } from "./disabled-features";
import { ReportActions } from "./report-actions";
import type { NormalizedQualityData } from "../uploads-api";

type FormatTab = "csv" | "pdf" | "mono";
type AnalyzerType = "finance" | "commerce";

const analyzerLabels: Record<AnalyzerType, string> = {
  finance: "Bank transactions export",
  commerce: "Store orders export",
};

function formatUploadedAt(date: Date | null) {
  if (!date) return "—";
  const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const isToday = date.toDateString() === new Date().toDateString();
  return isToday ? `Today, ${time}` : `${date.toLocaleDateString()}, ${time}`;
}

export interface DataQualityReportPageProps {
  theme: "dark" | "light";
  onToggleTheme: () => void;
  fileName: string;
  uploadedAt: Date | null;
  formatTab: FormatTab;
  analyzerType: AnalyzerType;
  report: NormalizedQualityData;
  onProceed: () => void;
  onFixReupload: () => void;
}

export function DataQualityReportPage({
  theme,
  onToggleTheme,
  fileName,
  uploadedAt,
  formatTab,
  analyzerType,
  report,
  onProceed,
  onFixReupload,
}: DataQualityReportPageProps) {
  const sourceLabel =
    formatTab === "pdf"
      ? "Bank statement"
      : formatTab === "mono"
        ? "Open banking (Mono)"
        : analyzerLabels[analyzerType];

  const summaryItems: FileSummaryItem[] = [
    { label: "File", value: fileName || "—" },
    { label: "Uploaded", value: formatUploadedAt(uploadedAt) },
    { label: "Analyzer", value: sourceLabel },
    { label: "Rows parsed", value: report.rowsParsed?.toLocaleString() ?? "—" },
    { label: "Rows rejected", value: report.rowsRejected?.toLocaleString() ?? "—" },
    { label: "Date range", value: report.dateRangeLabel },
  ];

  return (
    <main className={`scanwick-page upload-page ${theme === "light" ? "theme-light" : ""}`}>
      <AppTopbar theme={theme} onToggleTheme={onToggleTheme} />

      <section className="upload-main">
        <div className="dqr-inner">
          <div className="upload-heading">
            <h1>Data Quality Report</h1>
            <p>
              Every upload lands here first — so you always know exactly what
              Scanwick can and can't analyse.
            </p>
          </div>

          <FileSummaryGrid items={summaryItems} />

          <StatementChecks items={report.checks} />

          <MappingAppliedCard summary={report.mappingApplied} />

          <WarningsList items={report.warnings} />

          {report.disabledFeatures.length > 0 ? (
            <DisabledFeaturesList items={report.disabledFeatures} />
          ) : null}

          <ReportActions
            onProceed={onProceed}
            onFixReupload={onFixReupload}
            primaryLabel={report.state === "failed" ? "Resolve errors to proceed" : "Proceed to dashboard"}
            primaryDisabled={report.state === "failed"}
          />
        </div>
      </section>
    </main>
  );
}
