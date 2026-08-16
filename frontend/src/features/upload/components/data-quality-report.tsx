/**
 * Upload quality report — prototype screen 62.
 *
 * This answers "did we read the file correctly?". The statement audit
 * answers "does the statement reconcile?". They are different questions and
 * are deliberately not merged: a file can parse perfectly and still fail its
 * arithmetic, or parse badly and reconcile on the rows that survived.
 *
 * A held row is not a lost row. Warnings are recoverable and are named with
 * the field they came from; rejected rows are stated with a reason. Nothing
 * is dropped silently, and no percentage is reported without the underlying
 * rows being nameable.
 */

import { AppShell, Screen } from "@/features/shell/app-shell";
import { Btn, Card, Hint, Kpi, Pill, Row, ScreenHead, Stepper, Tbl } from "@/components/sw";
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
  fileName: string;
  uploadedAt: Date | null;
  formatTab: FormatTab;
  analyzerType: AnalyzerType;
  report: NormalizedQualityData;
  onProceed: () => void;
  onFixReupload: () => void;
}

export function DataQualityReportPage({
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

  const parsed = report.rowsParsed;
  const rejected = report.rowsRejected;
  const inFile = parsed !== null && rejected !== null ? parsed + rejected : parsed;
  const parsedPct = inFile && parsed !== null ? ((parsed / inFile) * 100).toFixed(1) : null;
  const failed = report.state === "failed";

  return (
    <AppShell>
      <Screen>
        <ScreenHead
          title="Upload quality report"
          meta="What happened when we read this file · distinct from the statement audit"
          tag="Ingestion"
        />
        <Stepper steps={["Add accounts", "Processing", "Review coverage", "Your money"]} current={2} />

        <Card style={{ marginBottom: 16, background: "var(--g50)" }}>
          <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>
            <b>This report answers "did we read the file correctly?"</b> The statement audit answers "does the statement
            reconcile?" They are different questions — a file can parse perfectly and still fail its arithmetic, or parse
            badly and reconcile on the rows that survived.
          </div>
        </Card>

        <Row cols={4} style={{ marginBottom: 16 }}>
          <Kpi label="Rows in file" value={inFile?.toLocaleString() ?? "—"} detail="detected in the text layer" />
          <Kpi
            label="Parsed"
            value={parsed?.toLocaleString() ?? "—"}
            detail={parsedPct ? `${parsedPct}%` : undefined}
            valueStyle={{ color: "var(--g600)" }}
          />
          <Kpi
            label="Warnings"
            value={report.warnings.length}
            detail="rows kept, flagged"
            valueStyle={report.warnings.length > 0 ? { color: "var(--warn)" } : undefined}
          />
          <Kpi
            label="Rejected rows"
            value={rejected?.toLocaleString() ?? "0"}
            detail="not written to the database"
          />
        </Row>

        <Row cols="21">
          <div>
            <Card
              title="Every warning, with its field"
              sub="Each one names the field it came from"
              style={{ marginBottom: 14 }}
            >
              {report.warnings.length === 0 ? (
                <Hint>No warnings. Every row in this file was read as the issuer printed it.</Hint>
              ) : (
                <Tbl>
                  <table className="stack">
                    <thead>
                      <tr>
                        <th>Field</th>
                        <th>Severity</th>
                        <th>What we saw</th>
                        <th>What we did</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.warnings.map((warning, index) => (
                        <tr
                          key={`${warning.field}-${index}`}
                          style={warning.severity === "critical" ? { background: "var(--warnbg)" } : undefined}
                        >
                          <td className="mono" data-l="Field">
                            {warning.field}
                          </td>
                          <td data-l="Severity">
                            <Pill tone={warning.severity === "critical" ? "c" : "n"}>
                              {warning.severity === "critical" ? "Needs attention" : "Noted"}
                            </Pill>
                          </td>
                          <td data-l="What we saw">{warning.description}</td>
                          <td data-l="What we did">{warning.fix}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Tbl>
              )}

              {report.warnings.length > 0 ? (
                <div
                  style={{
                    marginTop: 16,
                    padding: 13,
                    border: "1px solid #E4C77E",
                    background: "var(--warnbg)",
                    borderRadius: 8,
                  }}
                >
                  <b style={{ fontSize: 12.5, color: "#5C4A16" }}>
                    {report.warnings.length} thing{report.warnings.length === 1 ? "" : "s"} worth your attention
                  </b>
                  <div style={{ fontSize: 12.5, color: "#5C4A16", marginTop: 6 }}>
                    A flagged row is not a lost row. Re-uploading a cleaner export of the same period resolves these and
                    the rows count in full.
                  </div>
                  <div style={{ marginTop: 11 }}>
                    <Btn sm onClick={onFixReupload}>
                      Upload a cleaner export
                    </Btn>
                  </div>
                </div>
              ) : null}
            </Card>

            {report.disabledFeatures.length > 0 ? (
              <Card title="What this file cannot support" sub="Each one names the reason and what unlocks it">
                <Tbl>
                  <table className="stack">
                    <thead>
                      <tr>
                        <th>Feature</th>
                        <th>Why</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.disabledFeatures.map((feature) => (
                        <tr key={feature.name}>
                          <td data-l="Feature">
                            <b>{feature.name}</b>
                          </td>
                          <td data-l="Why">{feature.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Tbl>
                <Hint style={{ marginTop: 10 }}>
                  These render as unavailable across your analysis, with this reason attached — never as a zero.
                </Hint>
              </Card>
            ) : null}
          </div>

          <div>
            <Card title="How the file was read" style={{ marginBottom: 14 }}>
              <table>
                <tbody>
                  <tr>
                    <td>File</td>
                    <td className="num">{fileName || "—"}</td>
                  </tr>
                  <tr>
                    <td>Uploaded</td>
                    <td className="num">{formatUploadedAt(uploadedAt)}</td>
                  </tr>
                  <tr>
                    <td>Read as</td>
                    <td className="num">{sourceLabel}</td>
                  </tr>
                  <tr>
                    <td>Period covered</td>
                    <td className="num mono">{report.dateRangeLabel}</td>
                  </tr>
                  <tr>
                    <td>Confidence tier</td>
                    <td className="num">
                      <Pill tone="b">B</Pill>
                    </td>
                  </tr>
                </tbody>
              </table>
            </Card>

            <Card title="Checks on this file" style={{ marginBottom: 14 }}>
              <table>
                <tbody>
                  {report.checks.map((check) => (
                    <tr key={check.label}>
                      <td>{check.label}</td>
                      <td className="num">
                        <Pill tone={check.status === "pass" ? "a" : check.status === "warning" ? "c" : "d"}>
                          {check.badgeLabel ?? (check.status === "pass" ? "Consistent" : check.status === "warning" ? "Noted" : "Detected")}
                        </Pill>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            {report.mappingApplied ? (
              <Card title="How your columns were read" style={{ marginBottom: 14 }}>
                <table>
                  <tbody>
                    <tr>
                      <td>Columns mapped</td>
                      <td className="num">{report.mappingApplied.columns_mapped}</td>
                    </tr>
                    {report.mappingApplied.unmapped_headers.length > 0 ? (
                      <tr>
                        <td>Not used</td>
                        <td className="num mono">{report.mappingApplied.unmapped_headers.join(", ")}</td>
                      </tr>
                    ) : null}
                    {Object.entries(report.mappingApplied.value_rules_applied).map(([field, rule]) => (
                      <tr key={field}>
                        <td>{field.replace(/_/g, " ")}</td>
                        <td className="num mono">read as {rule.replace(/_/g, " ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            ) : null}

            <Card title="Next">
              {failed ? (
                <>
                  <Btn block onClick={onFixReupload}>
                    Resolve and re-upload
                  </Btn>
                  <Btn tone="gho" sm block style={{ marginTop: 8 }} onClick={onProceed}>
                    Continue with what was read
                  </Btn>
                  <Hint style={{ marginTop: 10 }}>
                    Continuing means your analysis is based on fewer rows than the file contained. Coverage will say so.
                  </Hint>
                </>
              ) : (
                <>
                  <Btn block onClick={onProceed}>
                    See my money
                  </Btn>
                  <Btn tone="sec" sm block style={{ marginTop: 8 }} onClick={onFixReupload}>
                    Add another statement
                  </Btn>
                </>
              )}
            </Card>


          </div>
        </Row>
      </Screen>
    </AppShell>
  );
}
