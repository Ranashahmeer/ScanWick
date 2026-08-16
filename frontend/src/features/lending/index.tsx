/**
 * Surface 2 — lending. Prototype screens 65 (institution home), 35
 * (assessments), 36 (new assessment), 37 (signal set), 38 (lender brief),
 * 39 (traceability), 40 (loan stacking) and 41 (borrower type).
 *
 * Rule R5 governs this whole surface: there is no composite figure, no
 * grade, no rating and no traffic light on a borrower. Signals with
 * evidence; the credit officer exercises judgement. The loan-readiness
 * endpoint does return a 0–100 score and a tier letter — neither reaches
 * any screen here.
 *
 * Wording on screen 40 is load-bearing: "detected", "evidence for your
 * review", "shape". Never fraud, never stacking abuse, never high-risk
 * borrower, never a red banner.
 */

import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { AppShell, Screen } from "@/features/shell/app-shell";
import {
  Bar,
  Btn,
  Card,
  Coverage,
  Empty,
  Field,
  Hint,
  Inp,
  Kpi,
  LoadFailed,
  Money,
  Na,
  Pill,
  Radio,
  Row,
  ScreenHead,
  SkeletonRows,
  Stepper,
  Tbl,
  Tier,
} from "@/components/sw";
import { money } from "@/components/sw/format";
import { useAuth } from "@/hooks/use-auth";
import {
  useAbm,
  useCashflowAnalysis,
  useDashboardSummary,
  useIncomeStability,
  useLenderBrief,
  useLoanReadiness,
} from "@/features/dashboard/bank-api";
import { coverageRows, useSelectedAccount } from "@/features/money/use-account";

export type LendingView =
  | "home"
  | "assessments"
  | "new"
  | "signals"
  | "brief"
  | "traceability"
  | "stacking"
  | "type";

const HEADINGS: Record<LendingView, { title: string; meta: string }> = {
  home: { title: "Institution home", meta: "What needs action today, and what is waiting on someone else" },
  assessments: { title: "Assessments", meta: "One assessment is one borrower across all their accounts" },
  new: { title: "New assessment", meta: "Consent first · then statements · then analysis" },
  signals: { title: "Signal set", meta: "Capacity, stability, obligations and conduct" },
  brief: { title: "Lender brief", meta: "A written summary of this borrower's accounts" },
  traceability: { title: "Traceability", meta: "Any figure → the transactions → the original statement row" },
  stacking: { title: "New borrowing", meta: "Credits from lender counterparties in this period" },
  type: { title: "Borrower type", meta: "How this borrower's statements read, with the evidence" },
};

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(n) ? n : null;
}

export function LendingPage({ view = "home" }: { view?: LendingView }) {
  const heading = HEADINGS[view] ?? HEADINGS.home;
  const { accountId, accounts } = useSelectedAccount();
  const navigate = useNavigate();

  const goto = (to: string, search?: Record<string, string>) =>
    navigate({ to, search: (search ?? {}) as never });

  return (
    <AppShell>
      <Screen>
        <ScreenHead title={heading.title} meta={heading.meta} tag="Surface 2" tagTone="s2" />
        {view === "assessments" ? (
          <Assessments accounts={accounts} onNew={() => goto("/lending", { view: "new" })} onOpen={() => goto("/lending", { view: "brief" })} />
        ) : view === "new" ? (
          <NewAssessment />
        ) : view === "signals" ? (
          <SignalSet accountId={accountId} accounts={accounts} onCoverage={() => goto("/money", { view: "coverage" })} />
        ) : view === "brief" ? (
          <LenderBriefView accountId={accountId} />
        ) : view === "traceability" ? (
          <Traceability accountId={accountId} />
        ) : view === "stacking" ? (
          <LoanStacking accountId={accountId} />
        ) : view === "type" ? (
          <BorrowerType accountId={accountId} />
        ) : (
          <InstitutionHome accounts={accounts} goto={goto} />
        )}
      </Screen>
    </AppShell>
  );
}

/* ---------------------------------------------------------- screen 65 */

function InstitutionHome({
  accounts,
  goto,
}: {
  accounts: ReturnType<typeof useSelectedAccount>["accounts"];
  goto: (to: string, search?: Record<string, string>) => void;
}) {
  const { user } = useAuth();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const firstName = user?.first_name ?? user?.email?.split("@")[0] ?? "there";

  return (
    <>
      <Card style={{ marginBottom: 16, background: "var(--g900)", color: "#fff", border: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
          <div>
            <div
              style={{ fontSize: 11, letterSpacing: ".7px", textTransform: "uppercase", color: "var(--g300)", fontWeight: 700 }}
            >
              {greeting}, {firstName}
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-.5px", marginTop: 5 }}>
              Nothing needs action today
            </div>
            <div style={{ fontSize: 12.5, color: "#CFE0D6", marginTop: 5 }}>
              No assessment is waiting on a borrower and no facility has an open signal.
            </div>
          </div>
          <Btn style={{ background: "var(--g300)", color: "var(--g900)" }} onClick={() => goto("/lending", { view: "new" })}>
            New assessment
          </Btn>
        </div>
      </Card>

      <Row cols="21">
        <div>
          <Card title="Needs action today" style={{ marginBottom: 14 }}>
            <Empty title="Nothing needs attention">
              No facility has an open signal.
            </Empty>
          </Card>

          <Card title="Assessments in progress">
            <Empty title="No assessment is in progress" actionLabel="Start one" onAction={() => goto("/lending", { view: "new" })}>
              Start with a borrower who has already applied. Nothing can be uploaded or analysed until their consent
              record exists.
            </Empty>
          </Card>
        </div>

        <div>
          <Card title="Portfolio at a glance" style={{ marginBottom: 14 }}>
            <table>
              <tbody>
                <tr>
                  <td>Facilities monitored</td>
                  <td className="num">0</td>
                </tr>
                <tr>
                  <td>Open signals</td>
                  <td className="num">0</td>
                </tr>
                <tr>
                  <td>Unacknowledged</td>
                  <td className="num">0</td>
                </tr>
                <tr>
                  <td>Accounts in analysis</td>
                  <td className="num">{accounts.length}</td>
                </tr>
              </tbody>
            </table>
            <Btn tone="sec" sm block style={{ marginTop: 12 }} onClick={() => goto("/portfolio")}>
              Open portfolio
            </Btn>
          </Card>

          <Card title="Jump to">
            <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              <Btn tone="gho" sm style={{ justifyContent: "flex-start" }} onClick={() => goto("/lending", { view: "assessments" })}>
                All assessments
              </Btn>
              <Btn tone="gho" sm style={{ justifyContent: "flex-start" }} onClick={() => goto("/portfolio")}>
                Monitoring portfolio
              </Btn>
              <Btn tone="gho" sm style={{ justifyContent: "flex-start" }} onClick={() => goto("/audit", { view: "institution-log" })}>
                Access log
              </Btn>
              <Btn tone="gho" sm style={{ justifyContent: "flex-start" }} onClick={() => goto("/institution")}>
                Team & roles
              </Btn>
            </div>
          </Card>
        </div>
      </Row>
    </>
  );
}

/* ---------------------------------------------------------- screen 35 */

function Assessments({
  accounts,
  onNew,
  onOpen,
}: {
  accounts: ReturnType<typeof useSelectedAccount>["accounts"];
  onNew: () => void;
  onOpen: () => void;
}) {
  return (
    <>
      <Row cols={4} style={{ marginBottom: 16 }}>
        <Kpi label="This cycle" value={accounts.length > 0 ? 1 : 0} detail="assessments created" />
        <Kpi label="Accounts consolidated" value={accounts.length} detail="across all assessments" />
        <Kpi
          label="Multi-account"
          value={accounts.length > 1 ? "Yes" : "No"}
          valueStyle={{ fontSize: 20 }}
          detail={accounts.length > 1 ? `${accounts.length} accounts in one picture` : "one account only"}
        />
        <Kpi label="Median turnaround" value={<Na reason="Turnaround is measured across completed assessments; there are not enough yet." />} valueStyle={{ fontSize: 16 }} />
      </Row>

      <Card
        title="Recent assessments"
        sub="Valid 30 days · re-run free within that window"
        action={<Btn onClick={onNew}>New assessment</Btn>}
      >
        {accounts.length === 0 ? (
          <Empty title="No assessments yet" actionLabel="New assessment" onAction={onNew}>
            Start with a borrower who has already applied.
          </Empty>
        ) : (
          <Tbl>
            <table className="stack">
              <thead>
                <tr>
                  <th>Subject</th>
                  <th className="num">Accounts</th>
                  <th>Tier</th>
                  <th>Audit</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td data-l="Subject">
                    <b>This workspace</b>
                    <Hint>Consolidated across every statement supplied</Hint>
                  </td>
                  <td className="num" data-l="Accounts">
                    {accounts.length}
                  </td>
                  <td data-l="Tier">
                    <Tier tier="B" />
                  </td>
                  <td data-l="Audit">
                    <Pill tone="n">See account audit</Pill>
                  </td>
                  <td data-l="Status">
                    <Pill tone="a">Complete</Pill>
                  </td>
                  <td>
                    <Btn tone="gho" sm onClick={onOpen}>
                      Open
                    </Btn>
                  </td>
                </tr>
              </tbody>
            </table>
          </Tbl>
        )}
      </Card>


    </>
  );
}

/* ---------------------------------------------------------- screen 36 */

function NewAssessment() {
  const [method, setMethod] = useState("link");
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [sent, setSent] = useState(false);

  return (
    <>
      <Stepper steps={["Borrower", "Consent", "Statements", "Assessment"]} current={1} />

      <Row cols={2}>
        <Card title="Borrower consent" sub="Required before any statement is analysed">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              setSent(true);
            }}
          >
            <Field label="Borrower name" id="borrower-name">
              <Inp id="borrower-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" />
            </Field>
            <Field label="Phone or email" id="borrower-contact">
              <Inp
                id="borrower-contact"
                value={contact}
                onChange={(e) => setContact(e.target.value)}
                placeholder="0803 000 0000"
              />
            </Field>

            <div className="field">
              <label>How consent is being given</label>
              <Radio
                name="consent-method"
                label="Send the borrower a link to consent themselves"
                checked={method === "link"}
                onChange={() => setMethod("link")}
                right={<Pill tone="a">Preferred</Pill>}
              />
              <Radio
                name="consent-method"
                label="Borrower is present and consenting on this device"
                checked={method === "present"}
                onChange={() => setMethod("present")}
              />
              <Radio
                name="consent-method"
                label="Upload a signed consent form"
                checked={method === "form"}
                onChange={() => setMethod("form")}
              />
            </div>

            <Btn type="submit" disabled={!name || !contact}>
              Send consent request
            </Btn>
            <Hint style={{ marginTop: 11 }}>
              Nothing can be uploaded or analysed until the consent record exists.
            </Hint>
            {sent ? (
              <div
                role="status"
                style={{
                  marginTop: 12,
                  padding: 11,
                  background: "var(--g50)",
                  border: "1px solid var(--g300)",
                  borderRadius: 8,
                  fontSize: 12.5,
                  color: "var(--g700)",
                }}
              >
                Consent request prepared for {name}. Sending is not available yet, so nothing has been sent.
              </div>
            ) : null}
          </form>
        </Card>

        <div>
          <Card title="What the borrower will be asked to agree to" style={{ marginBottom: 14 }}>
            <table>
              <tbody>
                <tr>
                  <td>
                    <b>ASSESSMENT</b>
                  </td>
                  <td>We analyse the statements they provide</td>
                </tr>
                <tr>
                  <td>
                    <b>SHARE TO NAMED RECIPIENT</b>
                  </td>
                  <td>
                    The result goes to <b>this institution only</b>
                  </td>
                </tr>
                <tr style={{ color: "var(--ink3)" }}>
                  <td>MONITORING</td>
                  <td>Not requested here — separate consent at disbursement</td>
                </tr>
              </tbody>
            </table>
            <Hint style={{ marginTop: 11 }}>
              Consent text version <span className="mono">v1.3</span> · expires after 30 days · revocable
            </Hint>
          </Card>


        </div>
      </Row>
    </>
  );
}

/* ---------------------------------------------------------- screen 37 */

function SignalSet({
  accountId,
  accounts,
  onCoverage,
}: {
  accountId: string | null;
  accounts: ReturnType<typeof useSelectedAccount>["accounts"];
  onCoverage: () => void;
}) {
  const summary = useDashboardSummary(accountId ?? "");
  const abm = useAbm(accountId ?? "");
  const stability = useIncomeStability(accountId ?? "");
  const cashflow = useCashflowAnalysis(accountId ?? "");
  const readiness = useLoanReadiness(accountId ?? "");

  if (!accountId) {
    return (
      <Card>
        <Empty title="No statements to assess">Add an account and its signal set is computed from the statements.</Empty>
      </Card>
    );
  }
  if (summary.isLoading) {
    return (
      <Card>
        <SkeletonRows rows={8} />
      </Card>
    );
  }
  if (summary.isError) return <LoadFailed onRetry={() => summary.refetch()} />;

  const trend = summary.data?.monthly_cashflow_trend ?? [];
  const avgTurnover = trend.length ? trend.reduce((s, m) => s + (num(m.inflow) ?? 0), 0) / trend.length : null;
  const sources = summary.data?.top_income_sources ?? [];
  const totalIn = num(summary.data?.inflows);
  const largestShare = totalIn && sources.length ? ((num(sources[0].total_inflow) ?? 0) / totalIn) * 100 : null;
  const monthsWithIncome = trend.filter((m) => (num(m.inflow) ?? 0) > 0).length;
  const abmData = abm.data?.data ?? null;
  const stabilityData = stability.data?.data ?? null;
  const coverage = readiness.data?.estimated_debt_coverage_indicator ?? null;
  const obligations = num(coverage?.estimated_monthly_debt_obligations);
  const dsr = obligations !== null && avgTurnover ? (obligations / avgTurnover) * 100 : null;

  const half = Math.floor(trend.length / 2);
  const earlier = trend.slice(0, half).reduce((s, m) => s + (num(m.inflow) ?? 0), 0);
  const later = trend.slice(trend.length - half).reduce((s, m) => s + (num(m.inflow) ?? 0), 0);
  const direction = half === 0 ? null : later > earlier * 1.05 ? "Rising" : later < earlier * 0.95 ? "Falling" : "Flat";

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
        <div style={{ display: "flex", gap: 22, flexWrap: "wrap" }}>
          <div>
            <div className="lab" style={{ fontSize: 10, color: "var(--ink3)", fontWeight: 700 }}>
              SOURCE TIER
            </div>
            <div style={{ marginTop: 4, display: "flex", gap: 4 }}>
              {accounts.map((a) => (
                <Tier key={a.id} tier="B" />
              ))}
            </div>
          </div>
          <div>
            <div className="lab" style={{ fontSize: 10, color: "var(--ink3)", fontWeight: 700 }}>
              COVERAGE
            </div>
            <div style={{ marginTop: 4, fontSize: 12 }}>
              {accounts.length} account{accounts.length === 1 ? "" : "s"} · {trend.length} months
            </div>
          </div>
        </div>
        <Btn tone="sec" sm onClick={onCoverage}>
          Full coverage statement
        </Btn>
      </Card>

      <Row cols={2}>
        <Card title="Capacity">
          <table>
            <tbody>
              <tr>
                <td>Consolidated inflow</td>
                <td className="num">
                  <Money value={totalIn} />
                </td>
              </tr>
              <tr>
                <td>Average monthly turnover</td>
                <td className="num">
                  <Money value={avgTurnover} reason="Needs a monthly breakdown." />
                </td>
              </tr>
              <tr>
                <td>Trend across period</td>
                <td className="num" style={{ color: direction === "Rising" ? "var(--g600)" : undefined }}>
                  {direction ?? <Na reason="Needs at least two months to compare." />}
                </td>
              </tr>
              <tr>
                <td>Average balance, 3mo</td>
                <td className="num">
                  <Money value={abmData?.abm_3m ?? null} reason="This source carries no running balance column." />
                </td>
              </tr>
              <tr>
                <td>Balance trend</td>
                <td className="num">{abmData?.trend ?? <Na reason="Needs a balance series." />}</td>
              </tr>
            </tbody>
          </table>
        </Card>

        <Card title="Stability">
          <table>
            <tbody>
              <tr>
                <td>Months with income</td>
                <td className="num">{trend.length ? `${monthsWithIncome} of ${trend.length}` : <Na />}</td>
              </tr>
              <tr>
                <td>Distinct income sources</td>
                <td className="num">{sources.length || <Na />}</td>
              </tr>
              <tr>
                <td>Largest payer concentration</td>
                <td className="num">{largestShare !== null ? `${largestShare.toFixed(1)}%` : <Na />}</td>
              </tr>
              <tr>
                <td>Month-to-month variability</td>
                <td className="num" style={{ textTransform: "capitalize" }}>
                  {stabilityData?.label ?? <Na reason="Income stability needs at least three months of data." />}
                </td>
              </tr>
              <tr>
                <td>Variation around the mean</td>
                <td className="num">
                  {stabilityData ? `${Math.round(stabilityData.cv_pct)}%` : <Na reason="Needs at least three months." />}
                </td>
              </tr>
            </tbody>
          </table>
        </Card>
      </Row>

      <Row cols={2} style={{ marginTop: 16 }}>
        <Card title="Obligations">
          <table>
            <tbody>
              <tr>
                <td>Monthly obligations detected</td>
                <td className="num">
                  <Money value={obligations} reason="No monthly obligation figure was produced for this run." />
                </td>
              </tr>
              <tr>
                <td>Estimated available income</td>
                <td className="num">
                  <Money value={num(coverage?.estimated_available_income)} reason="Needs an income and obligation figure." />
                </td>
              </tr>
              <tr>
                <td>
                  <b>Debt service ratio</b>
                </td>
                <td className="num">
                  <b>{dsr !== null ? `${dsr.toFixed(1)}%` : <Na reason="Needs both figures above." />}</b>
                </td>
              </tr>
            </tbody>
          </table>
          {coverage?.methodology_note ? <Hint style={{ marginTop: 10 }}>{coverage.methodology_note}</Hint> : null}
        </Card>

        <Card title="Conduct">
          <table>
            <tbody>
              <tr>
                <td>Recurring commitment share of outflow</td>
                <td className="num">
                  {cashflow.data?.recurring_vs_variable?.recurring_pct !== null &&
                  cashflow.data?.recurring_vs_variable?.recurring_pct !== undefined ? (
                    `${cashflow.data.recurring_vs_variable.recurring_pct}%`
                  ) : (
                    <Na reason="Needs a recurring-payment analysis." />
                  )}
                </td>
              </tr>
              <tr>
                <td>Expense concentration</td>
                <td className="num">
                  {cashflow.data?.expense_concentration_ratio_pct !== null &&
                  cashflow.data?.expense_concentration_ratio_pct !== undefined ? (
                    `${cashflow.data.expense_concentration_ratio_pct}%`
                  ) : (
                    <Na />
                  )}
                </td>
              </tr>
              <tr>
                <td>Cash buffer</td>
                <td className="num">
                  {cashflow.data?.cash_buffer_months !== null && cashflow.data?.cash_buffer_months !== undefined ? (
                    `${cashflow.data.cash_buffer_months.toFixed(1)} months`
                  ) : (
                    <Na reason="Needs a balance series." />
                  )}
                </td>
              </tr>
              <tr>
                <td>New borrowing in period</td>
                <td className="num">
                  <Pill tone="n">See new borrowing</Pill>
                </td>
              </tr>
            </tbody>
          </table>
        </Card>
      </Row>


    </>
  );
}

/* ---------------------------------------------------------- screen 38 */

function LenderBriefView({ accountId }: { accountId: string | null }) {
  const brief = useLenderBrief(accountId ?? "");
  const { accounts } = useSelectedAccount();

  if (!accountId) {
    return (
      <Card>
        <Empty title="No statements to brief on">A brief is written from a completed analysis.</Empty>
      </Card>
    );
  }
  if (brief.isLoading) {
    return (
      <Card>
        <SkeletonRows rows={10} />
      </Card>
    );
  }
  if (brief.isError || !brief.data) return <LoadFailed onRetry={() => brief.refetch()} />;

  const s = brief.data.sections;
  const overview = s.business_overview;
  const cash = s.cash_flow_analysis;
  const stability = s.income_stability;

  return (
    <Row cols="21">
      <Card style={{ lineHeight: 1.75, fontSize: 13.5 }}>
        <div style={{ paddingBottom: 14, borderBottom: "1px solid var(--line)", marginBottom: 16 }}>
          <b style={{ fontSize: 15 }}>{overview.bank_name ?? "Consolidated"} — assessment brief</b>
          <Hint>
            {overview.transactions_analyzed.toLocaleString()} transactions ·{" "}
            {overview.statement_period_start ?? "—"} to {overview.statement_period_end ?? "—"}
          </Hint>
        </div>

        <p>
          <b>The accounts analysed.</b> {accounts.length} account{accounts.length === 1 ? " was" : "s were"} consolidated,
          covering {overview.statement_period_start ?? "an unstated start"} to {overview.statement_period_end ?? "an unstated end"}.{" "}
          {overview.transactions_analyzed.toLocaleString()} transactions were read. Every account here is Tier B — a file
          whose structure matches what the issuing institution produces.
        </p>

        <p style={{ marginTop: 12 }}>
          <b>What the money shows.</b>{" "}
          {cash.cash_buffer_months !== null
            ? `The account holds roughly ${cash.cash_buffer_months.toFixed(1)} months of cover at its current outflow rate. `
            : "A cash-buffer figure could not be computed from these statements. "}
          {cash.abm_trend
            ? `Average balance is ${cash.abm_trend.trend} across the period, with a three-month average of ${money(cash.abm_trend.abm_3m) ?? "an unavailable figure"}. `
            : "No balance series was available, so average-balance figures are unavailable rather than zero. "}
          {stability
            ? `Month-to-month income is ${stability.label}, varying by ${Math.round(stability.cv_pct)}% around its own average.`
            : "Income stability could not be assessed — it needs at least three months of transactions."}
        </p>

        <p style={{ marginTop: 12 }}>
          <b>What supports lending.</b>{" "}
          {cash.recurring_vs_variable.recurring_pct !== null
            ? `${cash.recurring_vs_variable.recurring_pct}% of outflow is recurring and predictable, which makes a fixed repayment easier to place. `
            : ""}
          {cash.by_payment_mode.length > 0
            ? `Money moves through ${cash.by_payment_mode.length} distinct payment channels rather than one. `
            : ""}
          {stability?.label === "stable" ? "Income arrives consistently month to month." : ""}
        </p>

        <p style={{ marginTop: 12 }}>
          <b>What to question.</b>{" "}
          {s.loan_readiness_assessment.disabled_components.length > 0
            ? `These could not be assessed from the statements supplied: ${s.loan_readiness_assessment.disabled_components.join(", ")}. `
            : ""}
          {cash.expense_concentration_ratio_pct !== null && cash.expense_concentration_ratio_pct > 40
            ? `Spending is concentrated — ${cash.expense_concentration_ratio_pct}% of outflow goes to a small number of counterparties. `
            : ""}
          {stability?.label === "volatile" ? "Income arrives unevenly, which matters for choosing a repayment date. " : ""}
          {s.loan_readiness_assessment.disabled_components.length === 0 &&
          stability?.label !== "volatile" &&
          (cash.expense_concentration_ratio_pct ?? 0) <= 40
            ? "Nothing in these statements stands out as needing an answer before a decision."
            : ""}
        </p>

        <p style={{ marginTop: 12 }}>
          <b>What could not be determined.</b>{" "}
          {cash.abm_trend === null
            ? "No running balance column was available, so every balance figure is unavailable rather than estimated. "
            : ""}
          {stability === null ? "Income stability needs at least three months of data. " : ""}
          Coverage is limited to the accounts listed below and no others — money held in cash, or in an account not
          supplied, is not visible.
        </p>

        <div style={{ marginTop: 16, padding: 13, background: "var(--g50)", borderRadius: 8, fontSize: 12, color: "var(--ink2)" }}>
          This brief presents evidence from the borrower's own statements. It does not recommend approval or decline, does
          not state an amount to lend and does not score the borrower. {brief.data.data_source_footnote}
        </div>
      </Card>

      <div>
        <Coverage accounts={coverageRows(accounts)} compact />

        <Card title="Actions" style={{ marginTop: 14 }}>
          <Btn
            sm
            block
            style={{ marginBottom: 8 }}
            onClick={() => brief.data?.pdf_url && window.open(brief.data.pdf_url, "_blank", "noopener")}
            disabled={!brief.data?.pdf_url}
          >
            Download PDF
          </Btn>
          <Btn tone="sec" sm block style={{ marginBottom: 8 }} onClick={() => brief.refetch()}>
            Re-run assessment
          </Btn>
          <Hint style={{ marginTop: 10 }}>
            Re-running within the 30-day validity window does not consume a credit.
          </Hint>
        </Card>


      </div>
    </Row>
  );
}

/* ---------------------------------------------------------- screen 39 */

function Traceability({ accountId }: { accountId: string | null }) {
  const summary = useDashboardSummary(accountId ?? "");
  const { accounts } = useSelectedAccount();

  const trend = summary.data?.monthly_cashflow_trend ?? [];
  const avgTurnover = trend.length ? trend.reduce((s, m) => s + (num(m.inflow) ?? 0), 0) / trend.length : null;
  const split = summary.data?.credit_debit_split;
  const analysed = split ? split.credit_count + split.debit_count : null;

  return (
    <Row cols="12">
      <Card title="Drill path">
        <div style={{ fontSize: 12.5, lineHeight: 2.2 }}>
          <div>
            <b>Average monthly turnover</b>
            <div className="mono" style={{ color: "var(--ink3)" }}>
              {money(avgTurnover) ?? "unavailable"}
            </div>
          </div>
          <div style={{ paddingLeft: 14, borderLeft: "2px solid var(--g300)" }}>
            ↓ {trend.length} monthly totals
          </div>
          <div style={{ paddingLeft: 14, borderLeft: "2px solid var(--g300)" }}>
            ↓ {analysed?.toLocaleString() ?? "—"} transactions
          </div>
          <div style={{ paddingLeft: 14, borderLeft: "2px solid var(--g300)" }}>↓ {accounts.length} statements</div>
          <div style={{ paddingLeft: 14, borderLeft: "2px solid var(--g300)" }}>↓ original file, page &amp; row</div>
        </div>
        <Hint style={{ marginTop: 12 }}>
          Four steps from a headline figure to a printed line in the borrower's own bank statement.
        </Hint>
      </Card>

      <Card title="Monthly totals — opened" sub="Each month opens to the transactions that produced it">
        {trend.length === 0 ? (
          <Empty title="Nothing to trace yet">A traceable figure needs a completed analysis behind it.</Empty>
        ) : (
          <>
            <Tbl>
              <table className="stack">
                <thead>
                  <tr>
                    <th>Month</th>
                    <th className="num">In</th>
                    <th className="num">Out</th>
                    <th className="num">Net</th>
                  </tr>
                </thead>
                <tbody>
                  {[...trend].reverse().map((m) => {
                    const mi = num(m.inflow);
                    const mo = num(m.outflow);
                    return (
                      <tr key={m.month}>
                        <td className="mono" data-l="Month">
                          {m.month}
                        </td>
                        <td className="num" data-l="In">
                          <Money value={mi} />
                        </td>
                        <td className="num" data-l="Out">
                          <Money value={mo} />
                        </td>
                        <td className="num" data-l="Net">
                          <Money value={mi !== null && mo !== null ? mi - mo : null} signed />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Tbl>


          </>
        )}
      </Card>
    </Row>
  );
}

/* ---------------------------------------------------------- screen 40 */

const LENDER_PATTERN = /loan|credit|lend|quickcash|fairmoney|palmcredit|renmoney|carbon|branch|disburse/i;

function LoanStacking({ accountId }: { accountId: string | null }) {
  const summary = useDashboardSummary(accountId ?? "");

  const sources = summary.data?.top_income_sources ?? [];
  const lenderCredits = sources.filter((s) => LENDER_PATTERN.test(s.payee));
  const total = lenderCredits.reduce((sum, s) => sum + (num(s.total_inflow) ?? 0), 0);

  return (
    <Row cols="21">
      <Card
        title="Disbursement-shaped credits from lender counterparties"
        sub="Credits whose counterparty name matches a lender"
      >
        {summary.isLoading ? (
          <SkeletonRows rows={4} />
        ) : lenderCredits.length === 0 ? (
          <Empty title="No lender-shaped credit detected">
            No credit in this period came from a counterparty whose name matches a lender. That is what was observed — it
            is not a statement about borrowing that happened elsewhere.
          </Empty>
        ) : (
          <>
            <Tbl>
              <table className="stack">
                <thead>
                  <tr>
                    <th>Counterparty</th>
                    <th className="num">Total</th>
                    <th className="num">Credits</th>
                    <th>Shape</th>
                  </tr>
                </thead>
                <tbody>
                  {lenderCredits.map((credit) => (
                    <tr key={credit.payee}>
                      <td data-l="Counterparty">{credit.payee}</td>
                      <td className="num" data-l="Total">
                        <Money value={credit.total_inflow} />
                      </td>
                      <td className="num" data-l="Credits">
                        {credit.occurrence_count}
                      </td>
                      <td data-l="Shape">
                        <Pill tone="n">Lender counterparty</Pill>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Tbl>

            <div style={{ marginTop: 16, padding: 14, border: "1px solid var(--line)", borderRadius: 8, background: "#fff" }}>
              <b style={{ fontSize: 12.5 }}>
                Detected: {money(total)} in credits from {lenderCredits.length} distinct lender counterpart
                {lenderCredits.length === 1 ? "y" : "ies"}.
              </b>
              <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 7 }}>
                There are legitimate explanations for credits from a lender counterparty. This is evidence for your
                review, not a conclusion about the borrower. The transactions are listed above.
              </div>
            </div>
          </>
        )}
      </Card>

      <div>
        <Card title="Why a bureau would not show this" style={{ marginBottom: 14 }}>
          <table>
            <tbody>
              <tr>
                <td>Bank statement</td>
                <td className="num" style={{ color: "var(--g600)" }}>
                  Same week
                </td>
              </tr>
              <tr>
                <td>Bureau visibility</td>
                <td className="num">Next submission cycle</td>
              </tr>
            </tbody>
          </table>
          <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 11 }}>
            Bureau reporting follows submission cycles. Lending apps can disburse in minutes. Disbursement speed has
            outrun reporting speed — a statement is not on a cycle.
          </div>
        </Card>


      </div>
    </Row>
  );
}

/* ---------------------------------------------------------- screen 41 */

const TYPES = [
  {
    name: "The consistent trader",
    describe: "Regular turnover from many small customers, low obligations, disciplined saving.",
    score: (ev: Evidence) =>
      (ev.payers >= 10 ? 40 : ev.payers * 4) +
      (ev.largestShare !== null && ev.largestShare < 30 ? 25 : 0) +
      (ev.monthsWithIncome === ev.months && ev.months > 0 ? 20 : 0) +
      (ev.dsr !== null && ev.dsr < 20 ? 15 : 0),
  },
  {
    name: "The seasonal operator",
    describe: "Turnover concentrated into part of the year, quiet months in between.",
    score: (ev: Evidence) => (ev.cv !== null && ev.cv > 40 ? 55 : ev.cv !== null && ev.cv > 25 ? 30 : 10) + (ev.months >= 6 ? 15 : 0),
  },
  {
    name: "The single-contract dependent",
    describe: "Most income arrives from one counterparty on a regular schedule.",
    score: (ev: Evidence) => (ev.largestShare !== null ? Math.min(90, ev.largestShare * 1.8) : 5),
  },
  {
    name: "The salaried side-trader",
    describe: "One consistent monthly credit alongside irregular trading income.",
    score: (ev: Evidence) =>
      (ev.cv !== null && ev.cv < 25 ? 35 : 10) + (ev.largestShare !== null && ev.largestShare > 35 ? 25 : 0),
  },
  {
    name: "The revolving borrower",
    describe: "Repeated credits from lender counterparties and a high obligation load.",
    score: (ev: Evidence) => (ev.dsr !== null && ev.dsr > 35 ? 60 : ev.dsr !== null && ev.dsr > 20 ? 30 : 5),
  },
];

interface Evidence {
  payers: number;
  largestShare: number | null;
  months: number;
  monthsWithIncome: number;
  cv: number | null;
  dsr: number | null;
}

function BorrowerType({ accountId }: { accountId: string | null }) {
  const summary = useDashboardSummary(accountId ?? "");
  const stability = useIncomeStability(accountId ?? "");
  const readiness = useLoanReadiness(accountId ?? "");

  if (!accountId || summary.isLoading) {
    return (
      <Card>
        <SkeletonRows rows={6} />
      </Card>
    );
  }
  if (summary.isError || !summary.data) return <LoadFailed onRetry={() => summary.refetch()} />;

  const trend = summary.data.monthly_cashflow_trend ?? [];
  const sources = summary.data.top_income_sources ?? [];
  const totalIn = num(summary.data.inflows);
  const avgTurnover = trend.length ? trend.reduce((s, m) => s + (num(m.inflow) ?? 0), 0) / trend.length : null;
  const obligations = num(readiness.data?.estimated_debt_coverage_indicator?.estimated_monthly_debt_obligations);

  const ev: Evidence = {
    payers: sources.length,
    largestShare: totalIn && sources.length ? ((num(sources[0].total_inflow) ?? 0) / totalIn) * 100 : null,
    months: trend.length,
    monthsWithIncome: trend.filter((m) => (num(m.inflow) ?? 0) > 0).length,
    cv: stability.data?.data?.cv_pct ?? null,
    dsr: obligations !== null && avgTurnover ? (obligations / avgTurnover) * 100 : null,
  };

  const ranked = TYPES.map((type) => ({ ...type, fit: Math.max(0, Math.min(100, type.score(ev))) })).sort(
    (a, b) => b.fit - a.fit,
  );
  const best = ranked[0];
  const enoughEvidence = ev.months >= 3 && ev.payers > 0;

  return (
    <Row cols={2}>
      <Card title="Classification" sub="Against five behavioural types">
        {!enoughEvidence ? (
          <div
            style={{
              padding: 16,
              background: "var(--warnbg)",
              border: "1px dashed #E4C77E",
              borderRadius: 8,
              display: "flex",
              gap: 14,
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <Na reason="A behavioural classification needs at least three months of income across identified counterparties." />
            <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>
              There is not enough history to place this borrower against the five types. A classification drawn from too
              little data is a wrong answer that looks like an insight.
            </div>
          </div>
        ) : (
          <>
            <div
              style={{
                padding: 16,
                border: "2px solid var(--g500)",
                borderRadius: 10,
                background: "var(--g50)",
                marginBottom: 14,
              }}
            >
              <div className="lab" style={{ fontSize: 10, color: "var(--g700)", fontWeight: 700 }}>
                BEST FIT
              </div>
              <div style={{ fontSize: 17, fontWeight: 700, margin: "5px 0" }}>{best.name}</div>
              <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>{best.describe}</div>
            </div>

            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Fit</th>
                </tr>
              </thead>
              <tbody>
                {ranked.map((type) => (
                  <tr key={type.name}>
                    <td>{type.name}</td>
                    <td>
                      <Bar percent={type.fit} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </Card>

      <Card title="Evidence cited" sub="Every classification states what it is based on">
        <table>
          <tbody>
            <tr>
              <td>Distinct paying counterparties</td>
              <td className="num">{ev.payers || <Na />}</td>
            </tr>
            <tr>
              <td>Largest payer concentration</td>
              <td className="num">{ev.largestShare !== null ? `${ev.largestShare.toFixed(1)}%` : <Na />}</td>
            </tr>
            <tr>
              <td>Months with income</td>
              <td className="num">{ev.months ? `${ev.monthsWithIncome} of ${ev.months}` : <Na />}</td>
            </tr>
            <tr>
              <td>Income variation</td>
              <td className="num">
                {ev.cv !== null ? `${Math.round(ev.cv)}%` : <Na reason="Needs at least three months." />}
              </td>
            </tr>
            <tr>
              <td>Debt service ratio</td>
              <td className="num">
                {ev.dsr !== null ? `${ev.dsr.toFixed(1)}%` : <Na reason="Needs an obligation figure and average income." />}
              </td>
            </tr>
          </tbody>
        </table>
        <Hint style={{ marginTop: 12 }}>
          Descriptive, not predictive. It says what this borrower's statements look like — it does not forecast whether
          they will repay.
        </Hint>
      </Card>
    </Row>
  );
}

export default LendingPage;
