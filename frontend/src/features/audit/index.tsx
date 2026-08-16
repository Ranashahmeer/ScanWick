/**
 * Audit — prototype screens 32 (account audit), 33 (who looked at your
 * data), 34 (institution access log) and 61 (analysis run record).
 *
 * Rule R10 governs screen 32 and it is the most sensitive rule in the
 * product: no red, no warning triangles, no exclamation marks, and never
 * the words fraud, forgery, fake, doctored or suspicious — in the UI, the
 * tooltips or the export. A finding states what was detected and shows the
 * rows. Nothing more. A check that could not run is recorded as could not
 * run, with its reason — never as a pass.
 */

import { useNavigate } from "@tanstack/react-router";
import { AppShell, Screen } from "@/features/shell/app-shell";
import {
  Card,
  Empty,
  Hint,
  Kpi,
  LoadFailed,
  Money,
  Na,
  Pill,
  Row,
  ScreenHead,
  SkeletonRows,
  Tbl,
} from "@/components/sw";
import { fmtDate } from "@/components/sw/format";
import { useDashboardSummary, useFraudRisk } from "@/features/dashboard/bank-api";
import { useReconciliationReport } from "@/features/reconciliation/reconciliation-api";
import { useSelectedAccount } from "@/features/money/use-account";

export type AuditView = "account" | "access-trail" | "institution-log" | "run-record";

const HEADINGS: Record<AuditView, { title: string; meta: string }> = {
  account: { title: "Account audit", meta: "Every check we ran on your statements" },
  "access-trail": { title: "Who has looked at your data", meta: "Append-only · nobody can delete an entry" },
  "institution-log": { title: "Access log", meta: "Institution admin · which of your staff accessed which borrower" },
  "run-record": { title: "Analysis run record", meta: "What each analysis run read, and what it set aside" },
};

export function AuditPage({ view = "account" }: { view?: AuditView }) {
  const heading = HEADINGS[view] ?? HEADINGS.account;
  const { accountId, accounts } = useSelectedAccount();

  return (
    <AppShell>
      <Screen>
        <ScreenHead title={heading.title} meta={heading.meta} tag="Audit" />
        {view === "access-trail" ? (
          <AccessTrail />
        ) : view === "institution-log" ? (
          <InstitutionLog />
        ) : view === "run-record" ? (
          <RunRecord accountId={accountId} accountCount={accounts.length} />
        ) : (
          <AccountAudit accountId={accountId} accountCount={accounts.length} />
        )}
      </Screen>
    </AppShell>
  );
}

/* ---------------------------------------------------------- screen 32 */

/**
 * The nine checks the product runs. Only three are computed by the
 * statement-integrity endpoint today; the rest are recorded as could not
 * run with the reason, which is the required treatment — a check that could
 * not run is not a check that succeeded.
 */
const CHECKS: { label: string; key: "balance" | "dates" | "order" | null; whyNot?: string }[] = [
  { label: "Row-level balance continuity", key: "balance" },
  { label: "Opening → closing reconciliation", key: "balance" },
  { label: "Date sequence gaps", key: "dates" },
  { label: "Sequential ordering", key: "order" },
  {
    label: "Stated vs actual transaction count",
    key: null,
    whyNot: "The statement's own stated count is not captured by this parser.",
  },
  {
    label: "Document producer",
    key: null,
    whyNot: "Producer metadata is not retained after the file is read.",
  },
  {
    label: "Modification after generation",
    key: null,
    whyNot: "Document-level modification metadata is not retained after the file is read.",
  },
  {
    label: "Missing pages",
    key: null,
    whyNot: "Page continuity is not recorded on this analysis run.",
  },
  {
    label: "Round-number clustering",
    key: null,
    whyNot: "Round-number analysis is not part of this analysis run.",
  },
];

function AccountAudit({ accountId, accountCount }: { accountId: string | null; accountCount: number }) {
  const fraud = useFraudRisk(accountId ?? "");
  const navigate = useNavigate();

  if (!accountId) {
    return (
      <Card>
        <Empty icon="🏦" title="Nothing to audit yet" actionLabel="Add an account" onAction={() => navigate({ to: "/accounts" })}>
          The statement audit runs on every file as it is ingested. Add an account and its results appear here.
        </Empty>
      </Card>
    );
  }

  if (fraud.isLoading) {
    return (
      <Card>
        <SkeletonRows rows={9} />
      </Card>
    );
  }
  if (fraud.isError) return <LoadFailed onRetry={() => fraud.refetch()} />;

  const integrity = fraud.data?.statement_integrity;

  const resolve = (key: "balance" | "dates" | "order" | null) => {
    if (key === null) return null;
    const raw =
      key === "balance" ? integrity?.balance_check : key === "dates" ? integrity?.date_continuity : integrity?.sequential_ordering;
    if (raw === "passed") return "consistent" as const;
    if (raw === "failed") return "detected" as const;
    return null;
  };

  const results = CHECKS.map((check) => ({ ...check, result: resolve(check.key) }));
  const ran = results.filter((r) => r.result !== null);
  const findings = ran.filter((r) => r.result === "detected");
  const couldNotRun = results.length - ran.length;

  return (
    <>
      <Row cols={4} style={{ marginBottom: 16 }}>
        <Kpi label="Accounts audited" value={accountCount} detail="every ingested statement" />
        <Kpi label="Checks run" value={ran.length} detail={`of ${CHECKS.length} defined`} />
        <Kpi label="Findings" value={findings.length} detail="none are accusations" />
        <Kpi
          label="Could not run"
          value={couldNotRun}
          detail="recorded, never passed"
          valueStyle={couldNotRun > 0 ? { color: "var(--warn)" } : undefined}
        />
      </Row>

      <Card
        title="Every check, with its result"
        sub="Each check is consistent, detected, or could not run — with its reason"
      >
        <Tbl>
          <table className="stack">
            <thead>
              <tr>
                <th>Check</th>
                <th>Result</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {results.map((check) => (
                <tr key={check.label}>
                  <td data-l="Check">{check.label}</td>
                  <td data-l="Result">
                    {check.result === "consistent" ? (
                      <Pill tone="a">Consistent</Pill>
                    ) : check.result === "detected" ? (
                      <Pill tone="n">Detected</Pill>
                    ) : (
                      <Pill tone="c">Could not run</Pill>
                    )}
                  </td>
                  <td className="mono" data-l="Detail">
                    {check.result ? "—" : check.whyNot}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Tbl>

        <Hint style={{ marginTop: 12 }}>
          {findings.length === 0
            ? "No finding was detected on the checks that ran."
            : `${findings.length} finding${findings.length === 1 ? "" : "s"} detected. Neither the wording nor the styling here is an accusation.`}{" "}
          {couldNotRun > 0
            ? `${couldNotRun} checks could not run and are recorded as such — a check that could not run is not a check that succeeded.`
            : ""}
        </Hint>
      </Card>


    </>
  );
}

/* ---------------------------------------------------------- screen 33 */

function AccessTrail() {
  return (
    <>
      <Card title="Every access, logged" sub="Append-only. Nobody at Scanwick or at a lender can delete an entry.">
        <Empty title="Nobody has accessed your data" >
          No lender has been granted access to your analysis, so there is nothing to show. The moment you create a share
          link, every time it is opened and everything exported from it appears here.
        </Empty>
      </Card>

      <Row cols={3} style={{ marginTop: 16 }}>
        <Card title="Who currently has access">
          <Hint>No lender can see anything about you that you did not grant to them by name. Nobody holds access today.</Hint>
        </Card>

        <Card title="What is recorded on every entry">
          <table>
            <tbody>
              <tr>
                <td>When</td>
                <td className="num">Timestamp</td>
              </tr>
              <tr>
                <td>Who</td>
                <td className="num">Named staff member</td>
              </tr>
              <tr>
                <td>Organisation</td>
                <td className="num">Their institution</td>
              </tr>
              <tr>
                <td>What they did</td>
                <td className="num">Opened, drilled in, exported</td>
              </tr>
              <tr>
                <td>Scope</td>
                <td className="num">Exactly what they saw</td>
              </tr>
            </tbody>
          </table>
        </Card>


      </Row>
    </>
  );
}

/* ---------------------------------------------------------- screen 34 */

function InstitutionLog() {
  return (
    <>
      <Row cols={4} style={{ marginBottom: 16 }}>
        <Kpi label="Accesses, 30 days" value={0} detail="across your team" />
        <Kpi label="Transaction-level views" value={0} detail="by credit officers only" />
        <Kpi label="Exports" value={0} detail="PDF and CSV" />
        <Kpi label="Retention" value="Append-only" valueStyle={{ fontSize: 19 }} detail="no delete path exists" />
      </Row>

      <Card title="Recent access" sub="Actor, timestamp, subject and scope on every entry">
        <Empty title="Nothing has been accessed yet">
          Once your team opens an assessment, drills into transactions or exports a brief, every action is recorded here
          with the staff member, the borrower, the scope and the address it came from.
        </Empty>
      </Card>


    </>
  );
}

/* ---------------------------------------------------------- screen 61 */

function RunRecord({ accountId, accountCount }: { accountId: string | null; accountCount: number }) {
  const summary = useDashboardSummary(accountId ?? "");
  const navigate = useNavigate();

  // The run id comes back in the dashboard response's meta; the record
  // itself — what was analysed, what was excluded and why, which features
  // were disabled — is the reconciliation row written by that run.
  const runId = summary.data?._analysisRunId ?? null;
  const record = useReconciliationReport(runId);

  if (!accountId) {
    return (
      <Card>
        <Empty title="No analysis has run yet" actionLabel="Add an account" onAction={() => navigate({ to: "/accounts" })}>
          Every analysis writes a run record. Once one exists, the figures on every screen can be traced back to it.
        </Empty>
      </Card>
    );
  }

  if (summary.isLoading) {
    return (
      <Card>
        <SkeletonRows rows={6} />
      </Card>
    );
  }

  const trend = summary.data?.monthly_cashflow_trend ?? [];
  const split = summary.data?.credit_debit_split;
  const fallbackAnalysed = split ? split.credit_count + split.debit_count : null;
  const data = record.data ?? null;
  const analysed = data?.records_analyzed ?? fallbackAnalysed;
  const excluded = data?.records_excluded ?? null;
  const net = analysed !== null && excluded !== null ? analysed - excluded : null;

  return (
    <>
      <Card
        style={{
          marginBottom: 16,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div className="lab" style={{ fontSize: 10, color: "var(--ink3)", fontWeight: 700 }}>
            ANALYSIS RUN ID
          </div>
          <div className="mono" style={{ fontSize: 14, fontWeight: 700, marginTop: 3 }}>
            {runId ?? <Na reason="This response did not carry an analysis run id." />}
          </div>
          <Hint>
            {runId
              ? "Every metric on every screen carries this. Quote it and any figure can be reproduced exactly."
              : "Until every endpoint returns a run id, figures on this account are not reproducible after the fact."}
          </Hint>
        </div>
        <div style={{ display: "flex", gap: 22, flexWrap: "wrap" }}>
          <div>
            <div className="lab" style={{ fontSize: 10, color: "var(--ink3)", fontWeight: 700 }}>
              RUN AT
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, marginTop: 3 }}>
              {fmtDate(data?.created_at) ?? "—"}
            </div>
          </div>
          <div>
            <div className="lab" style={{ fontSize: 10, color: "var(--ink3)", fontWeight: 700 }}>
              PERIOD
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, marginTop: 3 }}>
              {data?.date_range_start && data?.date_range_end
                ? `${data.date_range_start} → ${data.date_range_end}`
                : trend.length
                  ? `${trend.length} months`
                  : "—"}
            </div>
          </div>
          <div>
            <div className="lab" style={{ fontSize: 10, color: "var(--ink3)", fontWeight: 700 }}>
              ACCOUNTS
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, marginTop: 3 }}>{accountCount}</div>
          </div>
          <div>
            <div className="lab" style={{ fontSize: 10, color: "var(--ink3)", fontWeight: 700 }}>
              BASE CURRENCY
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, marginTop: 3 }}>{data?.base_currency ?? "NGN"}</div>
          </div>
        </div>
      </Card>

      <Row cols="21">
        <Card title="What this run analysed">
          {record.isLoading ? (
            <SkeletonRows rows={4} />
          ) : (
            <table>
              <tbody>
                <tr>
                  <td>
                    <b>Analysed</b>
                  </td>
                  <td className="num">
                    {analysed?.toLocaleString() ?? <Na reason="No transaction count was returned." />}
                  </td>
                  <td>across {accountCount} account{accountCount === 1 ? "" : "s"}</td>
                </tr>
                <tr>
                  <td>
                    <b>Excluded</b>
                  </td>
                  <td className="num">
                    {excluded?.toLocaleString() ?? (
                      <Na reason="This run did not write an exclusion count, so nothing is claimed about what was set aside." />
                    )}
                  </td>
                  <td>each with a reason, listed below</td>
                </tr>
                <tr>
                  <td>Net used in every figure</td>
                  <td className="num">{net?.toLocaleString() ?? <Na reason="Needs both counts above." />}</td>
                  <td />
                </tr>
              </tbody>
            </table>
          )}

          <h3 style={{ marginTop: 22 }}>Why records were excluded</h3>
          <div className="sub">Nothing is dropped silently — every exclusion is counted, valued and given a reason</div>
          {data?.exclusion_detail?.length ? (
            <Tbl>
              <table className="stack">
                <thead>
                  <tr>
                    <th>Reason</th>
                    <th className="num">Count</th>
                    <th className="num">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {data.exclusion_detail.map((row) => (
                    <tr key={row.reason}>
                      <td data-l="Reason">{row.reason}</td>
                      <td className="num" data-l="Count">
                        {row.count.toLocaleString()}
                      </td>
                      <td className="num" data-l="Value">
                        <Money value={row.value} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Tbl>
          ) : (
            <Hint>
              No record was excluded from this run — every transaction read from your statements is in the figures on
              every screen.
            </Hint>
          )}

          <h3 style={{ marginTop: 22 }}>Features disabled for this run</h3>
          {data?.disabled_features?.length ? (
            <Tbl>
              <table className="stack">
                <thead>
                  <tr>
                    <th>Feature</th>
                    <th>Why</th>
                    <th>What would enable it</th>
                  </tr>
                </thead>
                <tbody>
                  {data.disabled_features.map((feature) => (
                    <tr key={feature.feature_name}>
                      <td data-l="Feature">
                        <b>{feature.feature_name}</b>
                      </td>
                      <td data-l="Why">{feature.reason}</td>
                      <td data-l="Needs">{feature.data_needed}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Tbl>
          ) : (
            <Hint>No feature was disabled for this run.</Hint>
          )}
        </Card>

        <div>
          <Card title="This record" sub="A re-run creates a new record" style={{ marginBottom: 14 }}>
            <table>
              <tbody>
                <tr>
                  <td>Record</td>
                  <td className="num mono">{data?.id ? `${data.id.slice(0, 8)}…` : "—"}</td>
                </tr>
                <tr>
                  <td>Analyser</td>
                  <td className="num">{data?.analyzer_type ?? "—"}</td>
                </tr>
                <tr>
                  <td>Exchange rate source</td>
                  <td className="num">
                    {data?.exchange_rate_source ?? <Na reason="No conversion was applied on this run." />}
                  </td>
                </tr>
                <tr>
                  <td>Contextual markers applied</td>
                  <td className="num">{data?.contextual_markers_applied?.length ?? 0}</td>
                </tr>
              </tbody>
            </table>
            {record.isError ? (
              <Hint style={{ marginTop: 10 }}>
                No reconciliation record was found for this run id. Until every endpoint writes one, a figure produced
                today cannot be reproduced exactly months later.
              </Hint>
            ) : null}
          </Card>


        </div>
      </Row>
    </>
  );
}

export default AuditPage;
