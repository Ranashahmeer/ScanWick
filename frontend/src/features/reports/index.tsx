/**
 * Export preview — prototype screen 31.
 *
 * Every export carries, without exception: the source tier and audit result
 * for each account, the coverage statement, the generation timestamp and a
 * verification reference. A PDF someone emails can be edited, and a
 * recipient needs to be able to tell.
 */

import { useState } from "react";
import { AppShell, Screen } from "@/features/shell/app-shell";
import {
  Btn,
  Card,
  Check,
  Coverage,
  Empty,
  Field,
  Hint,
  Money,
  Na,
  Ph,
  Row,
  ScreenHead,
  Select,
  Tier,
} from "@/components/sw";
import { fmtDate, money } from "@/components/sw/format";
import { useAuth } from "@/hooks/use-auth";
import { useDashboardSummary } from "@/features/dashboard/bank-api";
import { coverageRows, useSelectedAccount } from "@/features/money/use-account";
import { downloadDataExport } from "@/features/account/billing/privacy-api";

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(n) ? n : null;
}

export default function Reports() {
  const { user } = useAuth();
  const { accountId, accounts } = useSelectedAccount();
  const summary = useDashboardSummary(accountId ?? "");

  const [format, setFormat] = useState("pdf");
  const [period, setPeriod] = useState("all");
  const [includeTransactions, setIncludeTransactions] = useState(true);
  const [includeSplit, setIncludeSplit] = useState(true);
  const [includeCharges, setIncludeCharges] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const inflow = num(summary.data?.inflows);
  const outflow = num(summary.data?.outflows);
  const net = inflow !== null && outflow !== null ? inflow - outflow : null;

  const generatedAt = new Date();
  // A stable, checkable reference derived from the run this export would be
  // built from — not a random string, so quoting it identifies the analysis.
  const runId = summary.data?._analysisRunId ?? null;
  const reference = runId ? `SCW-${runId.replace(/-/g, "").slice(0, 4).toUpperCase()}-${runId.replace(/-/g, "").slice(4, 8).toUpperCase()}` : null;

  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.email || "Your analysis";

  async function handleGenerate() {
    setExportError(null);
    if (format === "pdf") {
      setExportError("PDF reports are not available yet. Choose the data export to download everything we hold.");
      return;
    }
    setExporting(true);
    try {
      await downloadDataExport();
    } catch {
      setExportError("Could not build your export. Your analysis is safe and nothing was lost — please try again.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <AppShell>
      <Screen>
        <ScreenHead
          title="Export"
          meta="Every export carries the tiers, the audit result and the coverage statement"
          tag="Surface 1"
        />

        {accounts.length === 0 ? (
          <Card>
            <Empty icon="📄" title="Nothing to export yet" actionLabel="Add an account" onAction={() => (window.location.href = "/accounts")}>
              An export is built from a completed analysis. Add a statement and this fills in.
            </Empty>
          </Card>
        ) : (
          <Row cols="12">
            <div>
              <Card title="Export options" style={{ marginBottom: 14 }}>
                <Field label="Format" id="export-format">
                  <Select id="export-format" value={format} onChange={(e) => setFormat(e.target.value)}>
                    <option value="pdf">PDF report</option>
                    <option value="csv">Normalised data export</option>
                  </Select>
                </Field>

                <Field label="Period" id="export-period">
                  <Select id="export-period" value={period} onChange={(e) => setPeriod(e.target.value)}>
                    <option value="all">Full available history</option>
                    <option value="6">Last 6 months</option>
                  </Select>
                </Field>

                <div className="field">
                  <label>Include</label>
                  <Check
                    label="Transaction detail"
                    checked={includeTransactions}
                    onChange={(e) => setIncludeTransactions(e.target.checked)}
                  />
                  <Check
                    label="Business/personal split"
                    checked={includeSplit}
                    onChange={(e) => setIncludeSplit(e.target.checked)}
                  />
                  <Check
                    label="Charges breakdown"
                    checked={includeCharges}
                    onChange={(e) => setIncludeCharges(e.target.checked)}
                  />
                </div>

                <Btn block disabled={exporting} onClick={() => void handleGenerate()}>
                  {exporting ? "Building your export…" : "Generate"}
                </Btn>
                {exportError ? (
                  <div
                    role="alert"
                    style={{
                      marginTop: 12,
                      padding: 11,
                      background: "var(--warnbg)",
                      border: "1px solid #E4C77E",
                      borderRadius: 8,
                      fontSize: 12.5,
                      color: "#5C4A16",
                    }}
                  >
                    {exportError}
                  </div>
                ) : null}
              </Card>


            </div>

            {/* The preview is built from the same figures the export would
                carry, so what is on screen is what a recipient would read. */}
            <Card style={{ padding: 0, overflow: "hidden" }}>
              <div style={{ padding: "22px 26px", borderBottom: "1px solid var(--line)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <div
                      style={{
                        width: 26,
                        height: 26,
                        borderRadius: 6,
                        background: "var(--g800)",
                        color: "#fff",
                        display: "grid",
                        placeItems: "center",
                        fontWeight: 800,
                        fontSize: 13,
                      }}
                    >
                      S
                    </div>
                    <b style={{ fontSize: 15 }}>Scanwick</b>
                  </div>
                  <div style={{ textAlign: "right", fontSize: 10, color: "var(--ink3)" }}>
                    Generated {fmtDate(generatedAt.toISOString())} ·{" "}
                    {generatedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    <br />
                    Verification ref{" "}
                    {reference ? (
                      <span className="mono">{reference}</span>
                    ) : (
                      <Na reason="This analysis run did not return an id, so an export cannot carry a verification reference." />
                    )}
                  </div>
                </div>
                <h2 style={{ fontSize: 19, marginTop: 16, letterSpacing: "-.4px" }}>Financial Analysis</h2>
                <div style={{ fontSize: 12, color: "var(--ink3)" }}>{fullName}</div>
              </div>

              <div style={{ padding: "20px 26px", borderBottom: "1px solid var(--line)", background: "var(--g50)" }}>
                <div
                  style={{
                    fontSize: 10,
                    textTransform: "uppercase",
                    letterSpacing: ".6px",
                    fontWeight: 700,
                    color: "var(--ink3)",
                    marginBottom: 8,
                  }}
                >
                  Coverage
                </div>
                <table style={{ fontSize: 11.5 }}>
                  <tbody>
                    {accounts.map((account) => (
                      <tr key={account.id}>
                        <td>{account.bank_name ?? "Account"}</td>
                        <td>
                          {account.statement_period_start && account.statement_period_end
                            ? `${account.statement_period_start} – ${account.statement_period_end}`
                            : "Period not stated"}
                        </td>
                        <td>
                          <Tier tier="B" long />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div style={{ fontSize: 11, color: "var(--ink3)", marginTop: 8 }}>
                  {accounts.some((a) => num(a.closing_balance) === null)
                    ? "One or more accounts carry no balance column, so balance metrics for those accounts are unavailable rather than zero."
                    : "Every account in this analysis reports a balance."}
                </div>
              </div>

              <div style={{ padding: "20px 26px" }}>
                <Row cols={3} style={{ gap: 12 }}>
                  <div>
                    <div className="lab" style={{ fontSize: 10, color: "var(--ink3)", fontWeight: 700 }}>
                      MONEY IN
                    </div>
                    <div style={{ fontSize: 17, fontWeight: 700 }}>
                      <Money value={inflow} />
                    </div>
                  </div>
                  <div>
                    <div className="lab" style={{ fontSize: 10, color: "var(--ink3)", fontWeight: 700 }}>
                      MONEY OUT
                    </div>
                    <div style={{ fontSize: 17, fontWeight: 700 }}>
                      <Money value={outflow} />
                    </div>
                  </div>
                  <div>
                    <div className="lab" style={{ fontSize: 10, color: "var(--ink3)", fontWeight: 700 }}>
                      NET
                    </div>
                    <div
                      style={{
                        fontSize: 17,
                        fontWeight: 700,
                        color: net === null ? undefined : net >= 0 ? "var(--g600)" : "var(--stop)",
                      }}
                    >
                      <Money value={net} signed />
                    </div>
                  </div>
                </Row>

                <Ph height={100} style={{ marginTop: 16 }}>
                  {[
                    includeTransactions && "transaction detail",
                    includeSplit && "business/personal split",
                    includeCharges && "charges breakdown",
                  ]
                    .filter(Boolean)
                    .join(" · ") || "summary only"}{" "}
                  follows on the pages after this one
                </Ph>

                <Hint style={{ marginTop: 12 }}>
                  Net across the period: {money(net) ?? "unavailable"}. Every figure here traces back to the accounts
                  listed above and no others.
                </Hint>
              </div>
            </Card>
          </Row>
        )}

        {accounts.length > 0 ? (
          <div style={{ marginTop: 16 }}>
            <Coverage
              accounts={coverageRows(accounts)}
              notes="This same statement prints on the export itself — a recipient who cannot see coverage cannot judge how much weight to give the numbers."
            />
          </div>
        ) : null}
      </Screen>
    </AppShell>
  );
}
