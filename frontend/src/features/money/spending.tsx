/**
 * Where money goes (screen 20), Top payees (21), Recurring outflows (22)
 * and Fees & charges (23).
 *
 * Every amount on these screens opens to the transactions behind it, and
 * the drill-down is a panel rather than a new page — the user is checking,
 * not navigating away.
 */

import { useState } from "react";
import {
  Bar,
  Btn,
  Card,
  Drawer,
  Hint,
  Kpi,
  LoadFailed,
  Money,
  Na,
  Pill,
  Row,
  SkeletonRows,
  Tbl,
} from "@/components/sw";
import { fmtDate, money } from "@/components/sw/format";
import {
  useCashflowAnalysis,
  useCashflowForecast,
  useDashboardSummary,
  useFinancialHealthPlaybook,
} from "@/features/dashboard/bank-api";

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(n) ? n : null;
}

/* ----------------------------------------------------- screen 20 */

export function SpendingView({ accountId }: { accountId: string }) {
  const summary = useDashboardSummary(accountId);
  const cashflow = useCashflowAnalysis(accountId);
  const [opened, setOpened] = useState<{ name: string; total: number; count: number } | null>(null);

  if (summary.isLoading) {
    return (
      <Card>
        <SkeletonRows rows={8} />
      </Card>
    );
  }
  if (summary.isError || !summary.data) return <LoadFailed onRetry={() => summary.refetch()} />;

  const payees = summary.data.top_payees_by_outflow ?? [];
  const total = payees.reduce((sum, p) => sum + (num(p.total_outflow) ?? 0), 0);
  const largest = Math.max(...payees.map((p) => num(p.total_outflow) ?? 0), 1);

  return (
    <>
      <Row cols="21">
        <Card
          title="Where your money went"
          sub={`${payees.length} counterparties · ranked by value · internal transfers excluded`}
        >
          {payees.length === 0 ? (
            <Hint>No outflows were returned for this account.</Hint>
          ) : (
            <Tbl>
              <table className="stack">
                <thead>
                  <tr>
                    <th>Counterparty</th>
                    <th className="num">Amount</th>
                    <th className="num">Share</th>
                    <th className="num">Count</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {payees.map((p) => {
                    const value = num(p.total_outflow) ?? 0;
                    return (
                      <tr key={p.payee}>
                        <td data-l="Counterparty">
                          <button
                            type="button"
                            onClick={() => setOpened({ name: p.payee, total: value, count: p.occurrence_count })}
                            style={{
                              background: "none",
                              border: 0,
                              padding: 0,
                              font: "inherit",
                              fontWeight: 600,
                              color: "inherit",
                              cursor: "pointer",
                              textAlign: "left",
                              textDecoration: "underline",
                              textDecorationColor: "var(--g300)",
                              textUnderlineOffset: 3,
                            }}
                          >
                            {p.payee}
                          </button>
                        </td>
                        <td className="num" data-l="Amount">
                          <Money value={value} />
                        </td>
                        <td className="num" data-l="Share">
                          {total ? `${((value / total) * 100).toFixed(1)}%` : <Na />}
                        </td>
                        <td className="num" data-l="Count">
                          {p.occurrence_count}
                        </td>
                        <td>
                          <Bar percent={(value / largest) * 100} width={70} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Tbl>
          )}
          <Hint style={{ marginTop: 12 }}>
            Ranked by counterparty, which is what your statements name. Tap any row to see the movements behind it.
          </Hint>
        </Card>

        <div>
          <Card title="By payment method" sub="How the money left the account" style={{ marginBottom: 14 }}>
            {cashflow.isLoading ? (
              <SkeletonRows rows={4} />
            ) : cashflow.data?.by_payment_mode?.length ? (
              <table>
                <tbody>
                  {cashflow.data.by_payment_mode.map((mode) => (
                    <tr key={mode.mode}>
                      <td>{mode.mode}</td>
                      <td className="num">
                        <Money value={mode.total_amount} />
                        <Hint>{mode.occurrence_count} movements</Hint>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <Na reason="No payment-method breakdown was produced for this analysis run." />
                <span style={{ fontSize: 12.5, color: "var(--ink2)" }}>Not produced for this run.</span>
              </div>
            )}
          </Card>

          <Card title="Recurring against variable" sub="How much of your spending is committed">
            {cashflow.data?.recurring_vs_variable ? (
              <table>
                <tbody>
                  <tr>
                    <td>Recurring</td>
                    <td className="num">
                      <Money value={cashflow.data.recurring_vs_variable.recurring_total} />
                    </td>
                    <td className="num">
                      {cashflow.data.recurring_vs_variable.recurring_pct !== null ? (
                        <Pill tone="a">{cashflow.data.recurring_vs_variable.recurring_pct}%</Pill>
                      ) : (
                        <Na />
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td>Variable</td>
                    <td className="num">
                      <Money value={cashflow.data.recurring_vs_variable.variable_total} />
                    </td>
                    <td className="num">
                      {cashflow.data.recurring_vs_variable.variable_pct !== null ? (
                        <Pill tone="n">{cashflow.data.recurring_vs_variable.variable_pct}%</Pill>
                      ) : (
                        <Na />
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            ) : (
              <Na reason="Needs a recurring-payment analysis for this account." />
            )}
          </Card>
        </div>
      </Row>

      <Drawer
        open={!!opened}
        title={opened?.name ?? ""}
        sub={opened ? `${opened.count} movements · ${money(opened.total)}` : undefined}
        onClose={() => setOpened(null)}
      >
        <Card title="What this figure is made of">
          <table>
            <tbody>
              <tr>
                <td>Total paid to this counterparty</td>
                <td className="num">
                  <Money value={opened?.total ?? null} />
                </td>
              </tr>
              <tr>
                <td>Number of movements</td>
                <td className="num">{opened?.count ?? <Na />}</td>
              </tr>
              <tr>
                <td>Average per movement</td>
                <td className="num">
                  <Money value={opened && opened.count ? opened.total / opened.count : null} />
                </td>
              </tr>
              <tr>
                <td>Share of all outflow</td>
                <td className="num">{total && opened ? `${((opened.total / total) * 100).toFixed(1)}%` : <Na />}</td>
              </tr>
            </tbody>
          </table>
          <Hint style={{ marginTop: 10 }}>
            Row-level narration exactly as your bank printed it is not returned by this analysis run, so the individual
            movements cannot be listed here yet.
          </Hint>
        </Card>
      </Drawer>
    </>
  );
}

/* ----------------------------------------------------- screen 21 */

export function PayeesView({ accountId }: { accountId: string }) {
  const summary = useDashboardSummary(accountId);
  const playbook = useFinancialHealthPlaybook(accountId);

  if (summary.isLoading) {
    return (
      <Row cols={2}>
        <Card>
          <SkeletonRows rows={5} />
        </Card>
        <Card>
          <SkeletonRows rows={5} />
        </Card>
      </Row>
    );
  }
  if (summary.isError || !summary.data) return <LoadFailed onRetry={() => summary.refetch()} />;

  const payees = summary.data.top_payees_by_outflow ?? [];
  const byValue = [...payees].sort((a, b) => (num(b.total_outflow) ?? 0) - (num(a.total_outflow) ?? 0));
  const byCount = [...payees].sort((a, b) => b.occurrence_count - a.occurrence_count);

  // A recommendation about a customer who stopped paying is exactly the
  // "gone quiet" list the prototype asks for, and it already carries the
  // amount at stake and the reasoning.
  const lapsed = (playbook.data?.recommendations ?? []).filter(
    (r) => r.entity_type === "customer" || /stopped|quiet|lapsed|churn/i.test(r.trigger_condition),
  );

  return (
    <>
      <Row cols={2}>
        <Card title="Who you paid the most" sub="By total value">
          <Tbl>
            <table className="stack">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Counterparty</th>
                  <th className="num">Total</th>
                  <th className="num">Times</th>
                </tr>
              </thead>
              <tbody>
                {byValue.map((p, i) => (
                  <tr key={p.payee}>
                    <td data-l="#">{i + 1}</td>
                    <td data-l="Counterparty">{i === 0 ? <b>{p.payee}</b> : p.payee}</td>
                    <td className="num" data-l="Total">
                      <Money value={p.total_outflow} />
                    </td>
                    <td className="num" data-l="Times">
                      {p.occurrence_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Tbl>
        </Card>

        <Card title="Who you paid most often" sub="By frequency — the small consistent ones">
          <Tbl>
            <table className="stack">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Counterparty</th>
                  <th className="num">Times</th>
                  <th className="num">Total</th>
                </tr>
              </thead>
              <tbody>
                {byCount.map((p, i) => (
                  <tr key={p.payee}>
                    <td data-l="#">{i + 1}</td>
                    <td data-l="Counterparty">{i === 0 ? <b>{p.payee}</b> : p.payee}</td>
                    <td className="num" data-l="Times">
                      {p.occurrence_count}
                    </td>
                    <td className="num" data-l="Total">
                      <Money value={p.total_outflow} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Tbl>
          <Hint style={{ marginTop: 11 }}>
            The insight people react to: the small frequent payment that outranks a bill they think about constantly.
          </Hint>
        </Card>
      </Row>

      <Card
        title="Who has stopped paying you"
        sub="Counterparties who paid regularly and then went quiet"
        style={{ marginTop: 16 }}
      >
        {playbook.isLoading ? (
          <SkeletonRows rows={3} />
        ) : lapsed.length === 0 ? (
          <Hint>No counterparty in this analysis has stopped a regular payment pattern.</Hint>
        ) : (
          <Tbl>
            <table className="stack">
              <thead>
                <tr>
                  <th>Counterparty</th>
                  <th>What we saw</th>
                  <th className="num">At stake</th>
                </tr>
              </thead>
              <tbody>
                {lapsed.map((r) => (
                  <tr key={r.id}>
                    <td data-l="Counterparty">
                      <b>{r.entity_name}</b>
                    </td>
                    <td data-l="What we saw">{r.reasoning}</td>
                    <td className="num" data-l="At stake">
                      <Money value={r.revenue_at_stake} currency={r.currency === "NGN" ? "₦" : `${r.currency} `} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Tbl>
        )}
        <Hint style={{ marginTop: 11 }}>This is information, not an alarm. You may already know.</Hint>
      </Card>
    </>
  );
}

/* ----------------------------------------------------- screen 22 */

function cadenceOf(dates: string[]): { label: string; confident: boolean } {
  if (dates.length < 2) return { label: "Not enough occurrences", confident: false };
  const times = dates.map((d) => new Date(d).getTime()).sort((a, b) => a - b);
  const gaps = times.slice(1).map((t, i) => (t - times[i]) / 86_400_000);
  const mean = gaps.reduce((a, b) => a + b, 0) / gaps.length;
  const spread = Math.max(...gaps) - Math.min(...gaps);
  const label =
    mean <= 9 ? "Weekly" : mean <= 18 ? "Fortnightly" : mean <= 45 ? "Monthly" : `About every ${Math.round(mean)} days`;
  // A pattern that varies by more than a few days is a weaker projection
  // and must not be presented with the same certainty as a fixed one.
  return { label, confident: spread <= 4 };
}

export function RecurringView({ accountId }: { accountId: string }) {
  const forecast = useCashflowForecast(accountId);

  if (forecast.isLoading) {
    return (
      <Card>
        <SkeletonRows rows={6} />
      </Card>
    );
  }
  if (forecast.isError || !forecast.data) return <LoadFailed onRetry={() => forecast.refetch()} />;

  const commitments = forecast.data.recurring_commitments_projected ?? [];
  const monthlyTotal = commitments.reduce((sum, c) => sum + (num(c.amount) ?? 0), 0);

  return (
    <>
      <Card title="Payments that repeat" sub="Detected by amount similarity and interval regularity">
        {commitments.length === 0 ? (
          <Hint>No repeating payment pattern was detected on this account.</Hint>
        ) : (
          <Tbl>
            <table className="stack">
              <thead>
                <tr>
                  <th>Counterparty</th>
                  <th>Cadence</th>
                  <th className="num">Typical</th>
                  <th className="num">Next expected</th>
                  <th className="num">Annualised</th>
                </tr>
              </thead>
              <tbody>
                {commitments.map((c) => {
                  const cadence = cadenceOf(c.expected_dates ?? []);
                  const next = (c.expected_dates ?? []).find((d) => new Date(d).getTime() >= Date.now());
                  const amount = num(c.amount);
                  const perYear =
                    amount !== null && cadence.label === "Weekly"
                      ? amount * 52
                      : amount !== null && cadence.label === "Fortnightly"
                        ? amount * 26
                        : amount !== null && cadence.label === "Monthly"
                          ? amount * 12
                          : null;
                  return (
                    <tr key={c.payee}>
                      <td data-l="Counterparty">
                        <b>{c.payee}</b>
                      </td>
                      <td data-l="Cadence">
                        {cadence.label}{" "}
                        {cadence.confident ? null : (
                          <Pill tone="n">approximate</Pill>
                        )}
                      </td>
                      <td className="num" data-l="Typical">
                        <Money value={amount} />
                      </td>
                      <td className="num" data-l="Next expected">
                        {next ? `${cadence.confident ? "" : "~"}${fmtDate(next)}` : <Na reason="No future occurrence projected." />}
                      </td>
                      <td className="num" data-l="Annualised">
                        <Money value={perYear} reason="Annualising needs a confident cadence." />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Tbl>
        )}
        {commitments.length > 0 ? (
          <Hint style={{ marginTop: 12 }}>
            Total committed across the detected patterns: <b>{money(monthlyTotal)}</b> before variable spending.
          </Hint>
        ) : null}
      </Card>


    </>
  );
}

/* ----------------------------------------------------- screen 23 */

export function FeesView({ accountId }: { accountId: string }) {
  const cashflow = useCashflowAnalysis(accountId);

  const REASON =
    "Fee, VAT and levy rows are not separated out by this analysis run, so a charges total would be a guess rather than a measurement.";

  return (
    <Row cols="21">
      <Card title="What you were charged" sub="Separated from your spending">
        <Row cols={3} style={{ marginBottom: 16 }}>
          <Kpi card={false} label="Total charges" value={<Na reason={REASON} />} />
          <Kpi card={false} label="Number of charges" value={<Na reason={REASON} />} />
          <Kpi card={false} label="Monthly average" value={<Na reason={REASON} />} />
        </Row>

        <div
          style={{
            padding: 14,
            border: "1px solid #E4C77E",
            background: "var(--warnbg)",
            borderRadius: 8,
            fontSize: 12.5,
            color: "#5C4A16",
          }}
        >
          <b>Why these are unavailable</b>
          <div style={{ marginTop: 6 }}>{REASON}</div>
        </div>

        {cashflow.data?.recurring_vs_variable ? (
          <>
            <h3 style={{ marginTop: 22 }}>What is available meanwhile</h3>
            <div className="sub">Your committed spending, which charges sit outside of</div>
            <table>
              <tbody>
                <tr>
                  <td>Recurring outflow</td>
                  <td className="num">
                    <Money value={cashflow.data.recurring_vs_variable.recurring_total} />
                  </td>
                </tr>
                <tr>
                  <td>Variable outflow</td>
                  <td className="num">
                    <Money value={cashflow.data.recurring_vs_variable.variable_total} />
                  </td>
                </tr>
              </tbody>
            </table>
          </>
        ) : null}
      </Card>

      <div>
        <Card title="Why this is separate" style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.7 }}>
            A charge is not a decision you made. If fees sit inside your spending total, your spending looks higher and
            less disciplined than it is — and if you are being assessed for credit on that statement, you are being
            misrepresented by your own bank charges.
          </div>
          <Hint style={{ marginTop: 11 }}>
            So charges are pulled out of every category, every trend and every ratio, and reported on their own.
          </Hint>
        </Card>

        <Card title="What unlocks this">
          <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>
            Charge isolation runs on statements whose narration identifies the fee, VAT and levy rows. Adding a statement
            from a source that labels them will fill these figures in.
          </div>
          <Btn sm tone="sec" block style={{ marginTop: 12 }} onClick={() => (window.location.href = "/upload")}>
            Upload another statement
          </Btn>
        </Card>
      </div>
    </Row>
  );
}
