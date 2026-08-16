/**
 * Consolidated view (prototype screen 18) and the coverage statement
 * (screen 19).
 *
 * Coverage is not a footnote, a tooltip or a modal — it sits above the fold
 * here and prints on every export. The closing balance is the sum of the
 * accounts that actually report one; any account without a balance column
 * renders the unavailable chip rather than a zero, and the coverage panel
 * says so.
 */

import {
  Card,
  Coverage,
  Hint,
  Kpi,
  Legend,
  Money,
  Na,
  Pill,
  Row,
  SkeletonKpis,
  SkeletonRows,
  Spark,
  Src,
  Tbl,
  Tier,
  LoadFailed,
} from "@/components/sw";
import { fmtMonth, money, srcMark } from "@/components/sw/format";
import { useDashboardSummary, type BankAccount } from "@/features/dashboard/bank-api";
import { NO_BALANCE_REASON, coverageRows } from "./use-account";

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(n) ? n : null;
}

export function ConsolidatedView({
  accountId,
  accounts,
  onAddAccount,
}: {
  accountId: string;
  accounts: BankAccount[];
  onAddAccount: () => void;
}) {
  const summary = useDashboardSummary(accountId);

  if (summary.isLoading) {
    return (
      <>
        <SkeletonKpis />
        <Card style={{ marginTop: 16 }}>
          <SkeletonRows rows={6} />
        </Card>
      </>
    );
  }

  if (summary.isError || !summary.data) {
    return <LoadFailed onRetry={() => summary.refetch()} />;
  }

  const data = summary.data;
  const inflow = num(data.inflows);
  const outflow = num(data.outflows);
  const net = inflow !== null && outflow !== null ? inflow - outflow : null;
  const trend = data.monthly_cashflow_trend ?? [];
  const months = trend.length;
  const avgNet = net !== null && months > 0 ? net / months : null;

  // Only accounts that actually report a balance contribute to the total.
  const withBalance = accounts.filter((a) => num(a.closing_balance) !== null);
  const withoutBalance = accounts.filter((a) => num(a.closing_balance) === null);
  const closing = withBalance.length
    ? withBalance.reduce((sum, a) => sum + (num(a.closing_balance) ?? 0), 0)
    : null;

  return (
    <>
      <Row cols={4} style={{ marginBottom: 16 }}>
        <Kpi
          label="Money in"
          value={<Money value={inflow} reason="No inflow was returned for this analysis run." />}
          detail={months ? `${months} months` : undefined}
        />
        <Kpi
          label="Money out"
          value={<Money value={outflow} reason="No outflow was returned for this analysis run." />}
          detail={months ? `${months} months` : undefined}
        />
        <Kpi
          label="Net position"
          value={<Money value={net} signed reason="Needs both inflow and outflow." />}
          detail={avgNet !== null ? `${money(avgNet)} average per month` : undefined}
          valueStyle={net !== null && net >= 0 ? { color: "var(--g600)" } : { color: "var(--stop)" }}
        />
        <Kpi
          label="Closing balance"
          value={<Money value={closing} reason={NO_BALANCE_REASON} />}
          detail={
            closing !== null
              ? `across ${withBalance.length} of ${accounts.length} account${accounts.length === 1 ? "" : "s"}`
              : "no account in this analysis reports a balance"
          }
        />
      </Row>

      {withoutBalance.length > 0 ? (
        <Card style={{ marginBottom: 16, borderLeft: "4px solid var(--warn)" }}>
          <b style={{ fontSize: 12.5 }}>
            {withoutBalance.length} account{withoutBalance.length === 1 ? "" : "s"} report no balance
          </b>
          <Hint>
            {withoutBalance.map((a) => a.bank_name ?? "Account").join(", ")} — {NO_BALANCE_REASON} Inflow and outflow are
            unaffected and are included above.
          </Hint>
        </Card>
      ) : null}

      <Row cols="21">
        <Card title="Month by month" sub="Inflow, outflow and net across the period analysed">
          {months === 0 ? (
            <Hint>No monthly breakdown was returned for this account.</Hint>
          ) : (
            <>
              <Spark values={trend.map((m) => num(m.inflow) ?? 0)} height={110} />
              <Legend items={trend.map((m) => fmtMonth(m.month))} />
              <Tbl>
                <table className="stack" style={{ marginTop: 14 }}>
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
                      const mn = mi !== null && mo !== null ? mi - mo : null;
                      return (
                        <tr key={m.month}>
                          <td data-l="Month">{fmtMonth(m.month)}</td>
                          <td className="num" data-l="In">
                            <Money value={mi} />
                          </td>
                          <td className="num" data-l="Out">
                            <Money value={mo} />
                          </td>
                          <td
                            className="num"
                            data-l="Net"
                            style={{ color: mn === null ? undefined : mn >= 0 ? "var(--g600)" : "var(--stop)" }}
                          >
                            <Money value={mn} signed />
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

        <div>
          <Card title="Your accounts" style={{ marginBottom: 14 }}>
            <table>
              <tbody>
                {accounts.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <Src mark={srcMark(a.bank_name)}>{a.bank_name ?? "Account"}</Src>
                      <Hint>
                        {a.statement_period_start && a.statement_period_end
                          ? `${a.statement_period_start} – ${a.statement_period_end}`
                          : "Period not stated"}
                      </Hint>
                    </td>
                    <td className="num">
                      <Tier tier="B" />
                      <div className="mono" style={{ marginTop: 4 }}>
                        {num(a.closing_balance) !== null ? (
                          money(num(a.closing_balance))
                        ) : (
                          <Na reason={NO_BALANCE_REASON} label="n/a" />
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button type="button" className="btn sec sm blk" style={{ marginTop: 12 }} onClick={onAddAccount}>
              Add another account
            </button>
          </Card>

          <Card title="Transaction mix" sub="Credits and debits in the period">
            <table>
              <tbody>
                <tr>
                  <td>Credits</td>
                  <td className="num">
                    {data.credit_debit_split?.credit_count ?? <Na />}{" "}
                    {data.credit_debit_split ? <Pill tone="a">{data.credit_debit_split.credit_pct}%</Pill> : null}
                  </td>
                </tr>
                <tr>
                  <td>Debits</td>
                  <td className="num">
                    {data.credit_debit_split?.debit_count ?? <Na />}{" "}
                    {data.credit_debit_split ? <Pill tone="n">{data.credit_debit_split.debit_pct}%</Pill> : null}
                  </td>
                </tr>
              </tbody>
            </table>
          </Card>
        </div>
      </Row>
    </>
  );
}

export function CoverageView({ accounts }: { accounts: BankAccount[] }) {
  const withoutBalance = accounts.filter(
    (a) => a.closing_balance === null || a.closing_balance === undefined,
  );
  const periods = accounts
    .map((a) => a.statement_period_start)
    .filter((p): p is string => Boolean(p))
    .sort();
  const periodsDiffer = new Set(periods).size > 1;

  return (
    <>
      <Coverage
        accounts={coverageRows(accounts)}
        notes={
          <>
            Every figure in your analysis is drawn from the accounts listed above and no others. Money held in cash, or in
            an account you have not added, is not visible to Scanwick.
          </>
        }
      />

      <Row cols={3} style={{ marginTop: 16 }}>
        <Card title="Where periods do not overlap">
          {periodsDiffer ? (
            <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>
              Your accounts do not all start on the same date. Any month covered by fewer than{" "}
              <b>{accounts.length} accounts</b> is not like-for-like with the rest, and monthly comparisons that include it
              should be read with that in mind.
            </div>
          ) : (
            <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>
              All {accounts.length} account{accounts.length === 1 ? "" : "s"} cover the same period, so every month is
              like-for-like.
            </div>
          )}
        </Card>

        <Card title="What could not be determined">
          <table>
            <tbody>
              {withoutBalance.length > 0 ? (
                withoutBalance.map((a) => (
                  <tr key={a.id}>
                    <td>{a.bank_name ?? "Account"} balance metrics</td>
                    <td className="num">
                      <Na reason={NO_BALANCE_REASON} />
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td>Balance metrics</td>
                  <td className="num">
                    <Pill tone="a">All available</Pill>
                  </td>
                </tr>
              )}
              {withoutBalance.map((a) => (
                <tr key={`${a.id}-continuity`}>
                  <td>Balance continuity check, {a.bank_name ?? "account"}</td>
                  <td className="num">
                    <Pill tone="n">Could not run</Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card title="Missing an account?" sub="Movements between your own accounts are only removed when we can see both sides.">
          <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>
            If a transfer out of one account has no matching credit anywhere in your analysis, it usually means an account
            is missing. Adding it makes every figure more accurate.
          </div>
        </Card>
      </Row>
    </>
  );
}
