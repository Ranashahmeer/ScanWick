/**
 * Business vs personal (screen 26), Balance behaviour (27) and Obligations
 * & contributory savings (29).
 *
 * Balance behaviour is where the unavailable rule bites hardest: an account
 * whose statement carries no running balance column has no average, no
 * minimum, no retention and no runway. Each of those renders the amber chip
 * with its reason, never ₦0, never a dash, never a blank cell.
 *
 * On screen 29, a fixed amount on a regular interval to a consistent
 * destination is contributory saving, not structuring. It is reported as
 * discipline and is never flagged.
 */

import {
  Bar,
  Card,
  Hint,
  Kpi,
  Legend,
  LoadFailed,
  Money,
  Na,
  Num,
  Pill,
  Row,
  SkeletonKpis,
  SkeletonRows,
  Spark,
  Tbl,
} from "@/components/sw";
import { fmtDateShort, money } from "@/components/sw/format";
import {
  useAbm,
  useCashflowAnalysis,
  useCashflowForecast,
  useDashboardSummary,
  useLoanReadiness,
} from "@/features/dashboard/bank-api";
import { NO_BALANCE_REASON } from "./use-account";

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(n) ? n : null;
}

/* ----------------------------------------------------- screen 26 */

export function ClassifyView({ accountId }: { accountId: string }) {
  const cashflow = useCashflowAnalysis(accountId);

  if (cashflow.isLoading) return <SkeletonKpis count={3} />;
  if (cashflow.isError || !cashflow.data) return <LoadFailed onRetry={() => cashflow.refetch()} />;

  const split = cashflow.data.business_vs_personal ?? [];
  const find = (name: string) => split.find((s) => s.category.toLowerCase().includes(name));
  const business = find("business");
  const personal = find("personal");
  const unclear = split.find((s) => /unclear|unknown|uncategor/i.test(s.category));

  const businessTotal = num(business?.total_amount);
  const personalTotal = num(personal?.total_amount);
  const combined =
    businessTotal !== null || personalTotal !== null ? (businessTotal ?? 0) + (personalTotal ?? 0) : null;

  return (
    <>
      <Row cols={3} style={{ marginBottom: 16 }}>
        <Kpi
          label="Business"
          value={<Money value={businessTotal} reason="No business classification was produced for this run." />}
          detail={business ? `${business.occurrence_count} transactions` : undefined}
          valueStyle={{ color: "var(--g600)" }}
        />
        <Kpi
          label="Personal"
          value={<Money value={personalTotal} reason="No personal classification was produced for this run." />}
          detail={personal ? `${personal.occurrence_count} transactions` : undefined}
        />
        <Kpi
          label="Combined"
          value={<Money value={combined} />}
          detail="What your balance actually reflects"
        />
      </Row>

      <Row cols="21">
        <Card title="Every transaction, classified" sub="Grouped by the classification applied to this analysis run">
          {split.length === 0 ? (
            <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
              <Na reason="Business/personal classification was not produced for this analysis run." />
              <span style={{ fontSize: 12.5, color: "var(--ink2)" }}>
                Nothing has been classified for this account yet.
              </span>
            </div>
          ) : (
            <Tbl>
              <table className="stack">
                <thead>
                  <tr>
                    <th>Class</th>
                    <th className="num">Amount</th>
                    <th className="num">Transactions</th>
                    <th className="num">Share</th>
                  </tr>
                </thead>
                <tbody>
                  {split.map((s) => {
                    const value = num(s.total_amount) ?? 0;
                    const allTotal = split.reduce((sum, x) => sum + (num(x.total_amount) ?? 0), 0);
                    const isUnclear = /unclear|unknown|uncategor/i.test(s.category);
                    return (
                      <tr key={s.category} style={isUnclear ? { background: "var(--warnbg)" } : undefined}>
                        <td data-l="Class">
                          <Pill tone={isUnclear ? "c" : /business/i.test(s.category) ? "a" : "n"}>{s.category}</Pill>
                        </td>
                        <td className="num" data-l="Amount">
                          <Money value={value} />
                        </td>
                        <td className="num" data-l="Transactions">
                          {s.occurrence_count}
                        </td>
                        <td className="num" data-l="Share">
                          {allTotal ? `${((value / allTotal) * 100).toFixed(1)}%` : <Na />}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Tbl>
          )}
        </Card>

        <div>
          {unclear ? (
            <Card title="Unclear transactions" sub={`${unclear.occurrence_count} remaining`} style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>
                Narration alone cannot tell us whether these are business or personal. Classifying them improves every
                figure here.
              </div>
              <div className="num" style={{ marginTop: 10, fontSize: 18, fontWeight: 700 }}>
                {money(num(unclear.total_amount))}
              </div>
            </Card>
          ) : null}


        </div>
      </Row>
    </>
  );
}

/* ----------------------------------------------------- screen 27 */

export function BalanceView({ accountId }: { accountId: string }) {
  const abm = useAbm(accountId);
  const cashflow = useCashflowAnalysis(accountId);
  const forecast = useCashflowForecast(accountId);
  const summary = useDashboardSummary(accountId);

  if (abm.isLoading || cashflow.isLoading) return <SkeletonKpis />;
  if (abm.isError) return <LoadFailed onRetry={() => abm.refetch()} />;

  const abmData = abm.data?.data ?? null;
  const abmReason =
    abm.data?.meta?.disabled_features?.[0]?.reason ?? NO_BALANCE_REASON;

  const daily = forecast.data?.daily_forecast ?? [];
  const balances = daily.map((d) => num(d.projected_balance) ?? 0);
  const minimum = balances.length ? Math.min(...balances) : null;
  const minimumDay = balances.length ? daily[balances.indexOf(Math.min(...balances))] : null;

  const runway = forecast.data?.cash_runway ?? null;
  const buffer = cashflow.data?.cash_buffer_months ?? null;
  const closing = num(summary.data?.balance?.closing);

  return (
    <>
      <Row cols={4} style={{ marginBottom: 16 }}>
        <Kpi
          label="Average balance"
          value={<Money value={abmData?.abm_3m ?? null} reason={abmReason} />}
          detail="3-month · carried across quiet days"
        />
        <Kpi
          label="Minimum balance"
          value={<Money value={minimum} reason="Needs a daily balance series for this account." />}
          detail={minimumDay ? `projected ${fmtDateShort(minimumDay.date)}` : undefined}
        />
        <Kpi
          label="6-month average"
          value={<Money value={abmData?.abm_6m ?? null} reason={abmReason} />}
          detail={
            abmData ? (
              <>
                Trend{" "}
                <span className={abmData.trend === "improving" ? "up" : abmData.trend === "declining" ? "dn" : undefined}>
                  {abmData.trend}
                </span>
              </>
            ) : undefined
          }
        />
        <Kpi
          label="Cash runway"
          value={
            <Num
              value={runway?.primary_scenario_months ?? buffer}
              decimals={1}
              suffix="months"
              reason="Needs a balance series and an average net outflow."
            />
          }
          detail="at current net outflow"
        />
      </Row>

      <Row cols="21">
        <Card title="Balance over the projection window" sub="Projected daily balance from the current position">
          {daily.length === 0 ? (
            <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
              <Na reason={abmReason} />
              <span style={{ fontSize: 12.5, color: "var(--ink2)" }}>
                No daily balance series is available for this account, so this chart cannot be drawn. It is left empty
                rather than filled with zeros.
              </span>
            </div>
          ) : (
            <>
              <Spark values={balances} height={120} />
              <Legend
                items={[fmtDateShort(daily[0].date) ?? "", fmtDateShort(daily[daily.length - 1].date) ?? ""]}
              />
              {minimumDay ? (
                <div style={{ marginTop: 14, fontSize: 12.5, color: "var(--ink2)" }}>
                  <b>Your lowest projected point is {fmtDateShort(minimumDay.date)}.</b> The balance is expected to reach{" "}
                  {money(minimum)} — worth knowing before you commit to a repayment date in that window.
                </div>
              ) : null}
            </>
          )}
        </Card>

        <div>
          <Card title="Averages across the period" style={{ marginBottom: 14 }}>
            <table>
              <tbody>
                <tr>
                  <td>3-month average</td>
                  <td className="num">
                    <Money value={abmData?.abm_3m ?? null} reason={abmReason} />
                  </td>
                </tr>
                <tr>
                  <td>6-month average</td>
                  <td className="num">
                    <Money value={abmData?.abm_6m ?? null} reason={abmReason} />
                  </td>
                </tr>
                <tr>
                  <td>12-month average</td>
                  <td className="num">
                    <Money value={abmData?.abm_12m ?? null} reason={abmReason} />
                  </td>
                </tr>
              </tbody>
            </table>
            <Hint style={{ marginTop: 9 }}>
              An account that holds value reads very differently from one that is a pass-through, and average balance
              alone does not tell them apart.
            </Hint>
          </Card>

          <Card title="Runway assumptions — always shown">
            <table>
              <tbody>
                <tr>
                  <td>Current balance</td>
                  <td className="num">
                    <Money value={closing} reason={NO_BALANCE_REASON} />
                  </td>
                </tr>
                <tr>
                  <td>Primary scenario</td>
                  <td className="num">
                    <Num value={runway?.primary_scenario_months ?? null} decimals={1} suffix="months" />
                  </td>
                </tr>
                <tr>
                  <td>Stress scenario</td>
                  <td className="num">
                    <Num value={runway?.stress_scenario_months ?? null} decimals={1} suffix="months" />
                  </td>
                </tr>
                <tr>
                  <td>Stress assumption</td>
                  <td className="num">{runway?.stress_assumption ?? <Na />}</td>
                </tr>
              </tbody>
            </table>
          </Card>
        </div>
      </Row>
    </>
  );
}

/* ----------------------------------------------------- screen 29 */

const SAVINGS_PATTERN = /ajo|esusu|adashe|thrift|contribut|savings/i;
const LENDER_PATTERN = /loan|credit|lend|quickcash|fairmoney|palmcredit|renmoney|carbon|branch/i;

export function ObligationsView({ accountId }: { accountId: string }) {
  const forecast = useCashflowForecast(accountId);
  const readiness = useLoanReadiness(accountId);
  const summary = useDashboardSummary(accountId);

  if (forecast.isLoading || readiness.isLoading) {
    return (
      <Card>
        <SkeletonRows rows={6} />
      </Card>
    );
  }

  const commitments = forecast.data?.recurring_commitments_projected ?? [];
  const loans = commitments.filter((c) => LENDER_PATTERN.test(c.payee));
  const savings = commitments.filter((c) => SAVINGS_PATTERN.test(c.payee));

  const coverage = readiness.data?.estimated_debt_coverage_indicator ?? null;
  const monthlyObligations = num(coverage?.estimated_monthly_debt_obligations);
  const availableIncome = num(coverage?.estimated_available_income);

  const trend = summary.data?.monthly_cashflow_trend ?? [];
  const avgIncome = trend.length
    ? trend.reduce((s, m) => s + (num(m.inflow) ?? 0), 0) / trend.length
    : null;
  const dsr =
    monthlyObligations !== null && avgIncome ? (monthlyObligations / avgIncome) * 100 : null;

  const savingsTotal = savings.reduce((s, c) => s + (num(c.amount) ?? 0), 0);
  const savingsOccurrences = savings.reduce((s, c) => s + (c.expected_dates?.length ?? 0), 0);

  return (
    <Row cols="21">
      <Card title="Existing loan repayments" sub="Detected from repayment-shaped outflows to lender counterparties">
        {loans.length === 0 ? (
          <Hint>No repayment-shaped outflow to a lender counterparty was detected on this account.</Hint>
        ) : (
          <Tbl>
            <table className="stack">
              <thead>
                <tr>
                  <th>Lender</th>
                  <th className="num">Monthly</th>
                  <th className="num">Occurrences seen</th>
                </tr>
              </thead>
              <tbody>
                {loans.map((c) => (
                  <tr key={c.payee}>
                    <td data-l="Lender">
                      <b>{c.payee}</b>
                    </td>
                    <td className="num" data-l="Monthly">
                      <Money value={c.amount} />
                    </td>
                    <td className="num" data-l="Occurrences">
                      {c.expected_dates?.length ?? <Na />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Tbl>
        )}

        <div
          style={{
            marginTop: 16,
            padding: 13,
            border: "1px solid var(--line)",
            borderRadius: 8,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 14,
          }}
        >
          <div>
            <b style={{ fontSize: 12.5 }}>Debt service ratio</b>
            <Hint>Monthly obligations ÷ monthly income</Hint>
          </div>
          <div className="num" style={{ fontSize: 20, fontWeight: 700 }}>
            {dsr !== null ? `${dsr.toFixed(1)}%` : <Na reason="Needs both a monthly obligation figure and average income." />}
          </div>
        </div>

        {monthlyObligations !== null && avgIncome ? (
          <Hint style={{ marginTop: 9 }}>
            {money(monthlyObligations)} of obligations against {money(avgIncome)} average monthly income. Both components
            are listed so the figure is checkable.
          </Hint>
        ) : null}

        {coverage?.methodology_note ? <Hint style={{ marginTop: 9 }}>{coverage.methodology_note}</Hint> : null}
        {availableIncome !== null ? (
          <Hint style={{ marginTop: 4 }}>Estimated available income: {money(availableIncome)}.</Hint>
        ) : null}
      </Card>

      <div>
        <Card
          title="Contributory savings — ajo"
          sub={savings.length ? savings.map((s) => s.payee).join(" · ") : "None detected on this account"}
          style={{ borderLeft: "4px solid var(--g500)", marginBottom: 14 }}
        >
          {savings.length === 0 ? (
            <Hint>
              No contributory savings pattern was detected. A regular fixed contribution to a consistent destination would
              be recognised here as discipline.
            </Hint>
          ) : (
            <>
              <div style={{ display: "flex", gap: 5, margin: "12px 0" }}>
                {Array.from({ length: Math.min(savingsOccurrences, 12) }).map((_, i) => (
                  <span key={i} style={{ flex: 1, height: 26, background: "var(--g500)", borderRadius: 3 }} />
                ))}
              </div>
              <table>
                <tbody>
                  <tr>
                    <td>Contribution</td>
                    <td className="num">
                      <Money value={savings[0].amount} />
                    </td>
                  </tr>
                  <tr>
                    <td>Occurrences detected</td>
                    <td className="num">{savingsOccurrences}</td>
                  </tr>
                  <tr>
                    <td>Total contributed</td>
                    <td className="num">{money(savingsTotal * Math.max(1, savingsOccurrences / savings.length))}</td>
                  </tr>
                </tbody>
              </table>
              <div
                style={{
                  marginTop: 12,
                  padding: 11,
                  background: "var(--g50)",
                  borderRadius: 8,
                  fontSize: 12.5,
                  color: "var(--g700)",
                }}
              >
                <b>This counts in your favour.</b> Uninterrupted contributions are evidence of financial discipline, and
                for many people they are the only sustained savings record that exists anywhere.
              </div>
            </>
          )}
        </Card>



        {loans.length > 0 ? (
          <Card title="Repayment record" style={{ marginTop: 14 }}>
            <table>
              <tbody>
                {loans.map((c) => (
                  <tr key={c.payee}>
                    <td>{c.payee}</td>
                    <td className="num">
                      <Pill tone="a">{c.expected_dates?.length ?? 0} on schedule</Pill>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Hint style={{ marginTop: 9 }}>
              Counted from the repayment-shaped outflows found in your statements, not from a lender's own records.
            </Hint>
          </Card>
        ) : null}

        <Card title="Committed each month" style={{ marginTop: 14 }}>
          <Bar
            percent={dsr ?? 0}
            color={dsr !== null && dsr > 40 ? "var(--stop)" : dsr !== null && dsr > 25 ? "var(--warn)" : undefined}
          />
          <Hint style={{ marginTop: 8 }}>
            {dsr === null
              ? "Your debt service ratio cannot be computed without both figures."
              : dsr < 15
                ? "Low. A lender reads this as room to take on a repayment."
                : dsr < 35
                  ? "Moderate. A lender will want to know what else is committed."
                  : "High. A new repayment would sit on top of a already-committed month."}
          </Hint>
        </Card>
      </div>
    </Row>
  );
}
