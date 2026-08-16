/**
 * Income & revenue patterns (screen 24), Seasonality (25) and Income
 * stability (64).
 *
 * Two rules govern this group. Seasonality is never drawn from fewer than
 * six months — a pattern shown from insufficient data is a wrong answer
 * that looks like an insight. And income stability shows the label and the
 * percentage only: the endpoint also returns a 0–100 figure, which is a
 * score, and PRD rule R5 prohibits any score, grade or rating from reaching
 * the interface.
 */

import {
  Card,
  Hint,
  Kpi,
  Legend,
  LoadFailed,
  Money,
  Na,
  Pill,
  Row,
  SkeletonKpis,
  SkeletonRows,
  Spark,
  Tbl,
} from "@/components/sw";
import { fmtMonth, money } from "@/components/sw/format";
import { useDashboardSummary, useIncomeStability } from "@/features/dashboard/bank-api";

const MIN_SEASONALITY_MONTHS = 6;
const MIN_STABILITY_MONTHS = 3;

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(n) ? n : null;
}

/* ----------------------------------------------------- screen 24 */

export function IncomeView({ accountId }: { accountId: string }) {
  const summary = useDashboardSummary(accountId);

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

  const sources = summary.data.top_income_sources ?? [];
  const trend = summary.data.monthly_cashflow_trend ?? [];
  const totalIn = num(summary.data.inflows);
  const monthsWithIncome = trend.filter((m) => (num(m.inflow) ?? 0) > 0).length;

  const largestShare =
    totalIn && sources.length ? ((num(sources[0].total_inflow) ?? 0) / totalIn) * 100 : null;
  const topFiveShare =
    totalIn && sources.length
      ? (sources.slice(0, 5).reduce((s, p) => s + (num(p.total_inflow) ?? 0), 0) / totalIn) * 100
      : null;

  // Direction across the period: compare the later half against the earlier.
  const half = Math.floor(trend.length / 2);
  const earlier = trend.slice(0, half).reduce((s, m) => s + (num(m.inflow) ?? 0), 0);
  const later = trend.slice(trend.length - half).reduce((s, m) => s + (num(m.inflow) ?? 0), 0);
  const direction = half === 0 ? null : later > earlier * 1.05 ? "Rising" : later < earlier * 0.95 ? "Falling" : "Flat";

  // Counterparty segmentation: value against frequency, both split at the
  // median so the quadrants describe this person's own book.
  const values = sources.map((s) => num(s.total_inflow) ?? 0).sort((a, b) => a - b);
  const counts = sources.map((s) => s.occurrence_count).sort((a, b) => a - b);
  const medianValue = values.length ? values[Math.floor(values.length / 2)] : 0;
  const medianCount = counts.length ? counts[Math.floor(counts.length / 2)] : 0;

  const quadrants = [
    { key: "hv-f", label: "HIGH VALUE · FREQUENT", note: "your core customers" },
    { key: "hv-o", label: "HIGH VALUE · OCCASIONAL", note: "worth re-contacting" },
    { key: "lv-f", label: "LOW VALUE · FREQUENT", note: "steady small buyers" },
    { key: "lv-o", label: "LOW VALUE · OCCASIONAL", note: "one-off buyers" },
  ].map((q) => {
    const members = sources.filter((s) => {
      const highValue = (num(s.total_inflow) ?? 0) >= medianValue;
      const frequent = s.occurrence_count >= medianCount;
      return (
        (q.key === "hv-f" && highValue && frequent) ||
        (q.key === "hv-o" && highValue && !frequent) ||
        (q.key === "lv-f" && !highValue && frequent) ||
        (q.key === "lv-o" && !highValue && !frequent)
      );
    });
    return {
      ...q,
      count: members.length,
      total: members.reduce((s, m) => s + (num(m.total_inflow) ?? 0), 0),
    };
  });

  return (
    <>
      <Row cols={2} style={{ marginBottom: 16 }}>
        <Card title="Income sources" sub="Grouped by counterparty">
          {sources.length === 0 ? (
            <Hint>No income sources were returned for this account.</Hint>
          ) : (
            <Tbl>
              <table className="stack">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th className="num">Times</th>
                    <th className="num">Total</th>
                    <th className="num">Share</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((s, i) => {
                    const value = num(s.total_inflow) ?? 0;
                    return (
                      <tr key={s.payee}>
                        <td data-l="Source">{i === 0 ? <b>{s.payee}</b> : s.payee}</td>
                        <td className="num" data-l="Times">
                          {s.occurrence_count}
                        </td>
                        <td className="num" data-l="Total">
                          <Money value={value} />
                        </td>
                        <td className="num" data-l="Share">
                          {totalIn ? `${((value / totalIn) * 100).toFixed(1)}%` : <Na />}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Tbl>
          )}
        </Card>

        <Card title="Revenue pattern" sub="The shape of income over the period">
          <table>
            <tbody>
              <tr>
                <td>Distinct paying counterparties</td>
                <td className="num">{sources.length || <Na />}</td>
              </tr>
              <tr>
                <td>Largest payer share of income</td>
                <td className="num">{largestShare !== null ? `${largestShare.toFixed(1)}%` : <Na />}</td>
              </tr>
              <tr>
                <td>Top 5 payers share</td>
                <td className="num">{topFiveShare !== null ? `${topFiveShare.toFixed(1)}%` : <Na />}</td>
              </tr>
              <tr>
                <td>Months with income</td>
                <td className="num">
                  {trend.length ? `${monthsWithIncome} of ${trend.length}` : <Na />}
                </td>
              </tr>
              <tr>
                <td>Direction across the period</td>
                <td className="num" style={{ color: direction === "Rising" ? "var(--g600)" : undefined }}>
                  {direction ?? <Na reason="Needs at least two months to compare." />}
                </td>
              </tr>
            </tbody>
          </table>
          {largestShare !== null ? (
            <Hint style={{ marginTop: 11 }}>
              {largestShare < 30
                ? "Income is not concentrated in one payer — a strength worth knowing."
                : "One payer accounts for a large share of income. A lender will ask what happens if they stop."}
            </Hint>
          ) : null}
        </Card>
      </Row>

      <Card title="Counterparty segmentation" sub="Paying counterparties grouped by value and frequency">
        <Row cols={4}>
          {quadrants.map((q) => (
            <div key={q.key} style={{ padding: 13, border: "1px solid var(--line)", borderRadius: 8 }}>
              <div className="lab" style={{ fontSize: 11, color: "var(--ink3)", fontWeight: 600 }}>
                {q.label}
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, margin: "5px 0" }}>{q.count}</div>
              <Hint>
                {money(q.total)} · {q.note}
              </Hint>
            </div>
          ))}
        </Row>
        <Hint style={{ marginTop: 12 }}>
          Split at the median of your own book, so these quadrants describe this account rather than a generic threshold.
        </Hint>
      </Card>
    </>
  );
}

/* ----------------------------------------------------- screen 64 */

export function StabilityView({ accountId }: { accountId: string }) {
  const stability = useIncomeStability(accountId);
  const summary = useDashboardSummary(accountId);

  if (stability.isLoading || summary.isLoading) return <SkeletonKpis />;
  if (stability.isError) return <LoadFailed onRetry={() => stability.refetch()} />;

  const trend = summary.data?.monthly_cashflow_trend ?? [];
  const inflows = trend.map((m) => num(m.inflow) ?? 0);
  const monthsWithIncome = inflows.filter((v) => v > 0).length;
  const mean = inflows.length ? inflows.reduce((a, b) => a + b, 0) / inflows.length : null;
  const highest = inflows.length ? Math.max(...inflows) : null;
  const lowest = inflows.length ? Math.min(...inflows) : null;

  // The endpoint reports this as a disabled feature under three months, in
  // which case data is null and the reason is what we render.
  const disabled = stability.data?.data == null;
  const reason =
    stability.data?.meta?.disabled_features?.[0]?.reason ??
    `Income stability needs at least ${MIN_STABILITY_MONTHS} months of transactions to be meaningful.`;
  const result = stability.data?.data ?? null;

  const cv = result?.cv_pct ?? null;
  const label = result?.label ?? null;
  const sd = mean !== null && cv !== null ? (cv / 100) * mean : null;
  const insideBand =
    mean !== null && sd !== null ? inflows.filter((v) => Math.abs(v - mean) <= sd).length : null;

  const half = Math.floor(trend.length / 2);
  const earlier = trend.slice(0, half).reduce((s, m) => s + (num(m.inflow) ?? 0), 0);
  const later = trend.slice(trend.length - half).reduce((s, m) => s + (num(m.inflow) ?? 0), 0);
  const direction = half === 0 ? null : later > earlier * 1.05 ? "Rising" : later < earlier * 0.95 ? "Falling" : "Flat";

  return (
    <>
      <Row cols={4} style={{ marginBottom: 16 }}>
        <Kpi
          label="Stability"
          value={label ? label[0].toUpperCase() + label.slice(1) : <Na reason={reason} />}
          valueStyle={{ fontSize: 22 }}
          detail={cv !== null ? `variation of ${Math.round(cv)}% around the mean` : "not enough history yet"}
        />
        <Kpi
          label="Months with income"
          value={trend.length ? `${monthsWithIncome} of ${trend.length}` : <Na />}
          detail={monthsWithIncome === trend.length && trend.length > 0 ? "no month without earnings" : undefined}
        />
        <Kpi
          label="Highest month"
          value={<Money value={highest} reason="Needs a monthly breakdown." />}
        />
        <Kpi label="Lowest month" value={<Money value={lowest} reason="Needs a monthly breakdown." />} />
      </Row>

      <Row cols="21">
        <Card
          title="Monthly income against your own average"
          sub={sd !== null ? "The band shows one standard deviation either side of the mean" : "Monthly inflow"}
        >
          {trend.length === 0 ? (
            <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
              <Na reason="No monthly breakdown was returned." />
              <span style={{ fontSize: 12.5, color: "var(--ink2)" }}>Nothing to plot yet.</span>
            </div>
          ) : (
            <>
              <div style={{ position: "relative", height: 130, margin: "16px 0" }}>
                {mean !== null && sd !== null && highest ? (
                  <div
                    style={{
                      position: "absolute",
                      left: 0,
                      right: 0,
                      bottom: `${Math.max(0, ((mean - sd) / highest) * 100)}%`,
                      height: `${Math.min(100, ((2 * sd) / highest) * 100)}%`,
                      background: "var(--g100)",
                      borderTop: "1px dashed var(--g500)",
                      borderBottom: "1px dashed var(--g500)",
                    }}
                  />
                ) : null}
                <Spark values={inflows} height={130} style={{ position: "relative" }} />
              </div>
              <Legend items={trend.map((m) => `${fmtMonth(m.month)} ${money(num(m.inflow))}`)} />

              <Tbl>
                <table className="stack" style={{ marginTop: 18 }}>
                  <thead>
                    <tr>
                      <th>Measure</th>
                      <th className="num">Value</th>
                      <th>Reading</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td data-l="Measure">Average monthly income</td>
                      <td className="num" data-l="Value">
                        <Money value={mean} />
                      </td>
                      <td data-l="Reading" />
                    </tr>
                    <tr>
                      <td data-l="Measure">Variation around the mean</td>
                      <td className="num" data-l="Value">
                        {cv !== null ? `${Math.round(cv)}%` : <Na reason={reason} />}
                      </td>
                      <td data-l="Reading">
                        {label ? (
                          <Pill tone={label === "stable" ? "a" : label === "moderate" ? "c" : "d"}>
                            {label[0].toUpperCase() + label.slice(1)}
                          </Pill>
                        ) : null}
                      </td>
                    </tr>
                    <tr>
                      <td data-l="Measure">Months inside the band</td>
                      <td className="num" data-l="Value">
                        {insideBand !== null ? `${insideBand} of ${trend.length}` : <Na reason={reason} />}
                      </td>
                      <td data-l="Reading" />
                    </tr>
                    <tr>
                      <td data-l="Measure">Direction across the period</td>
                      <td className="num" data-l="Value">
                        {direction ?? <Na reason="Needs at least two months." />}
                      </td>
                      <td data-l="Reading">{direction === "Rising" ? "later months above earlier" : ""}</td>
                    </tr>
                  </tbody>
                </table>
              </Tbl>
            </>
          )}
        </Card>

        <div>
          <Card title="How the band is set" style={{ marginBottom: 14 }}>
            <table>
              <tbody>
                <tr>
                  <td>Coefficient of variation under 20%</td>
                  <td>
                    <Pill tone="a">Stable</Pill>
                  </td>
                </tr>
                <tr>
                  <td>20% to 40%</td>
                  <td>
                    <Pill tone="c">Moderate</Pill>
                  </td>
                </tr>
                <tr>
                  <td>Over 40%</td>
                  <td>
                    <Pill tone="d">Volatile</Pill>
                  </td>
                </tr>
                <tr>
                  <td>Minimum data</td>
                  <td className="num">{MIN_STABILITY_MONTHS} months</td>
                </tr>
              </tbody>
            </table>
            <Hint style={{ marginTop: 10 }}>
              Coefficient of variation of monthly inflows — the spread divided by the average.
            </Hint>
          </Card>

          {disabled ? (
            <div
              style={{
                padding: 16,
                background: "var(--warnbg)",
                border: "1px dashed #E4C77E",
                borderRadius: 8,
                display: "flex",
                gap: 14,
                alignItems: "center",
              }}
            >
              <Na reason={reason} />
              <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>{reason}</div>
            </div>
          ) : (
            null
          )}
        </div>
      </Row>
    </>
  );
}

/* ----------------------------------------------------- screen 25 */

export function SeasonalityView({ accountId }: { accountId: string }) {
  const summary = useDashboardSummary(accountId);

  if (summary.isLoading) {
    return (
      <Row cols={2}>
        <Card>
          <SkeletonRows rows={4} />
        </Card>
        <Card>
          <SkeletonRows rows={4} />
        </Card>
      </Row>
    );
  }
  if (summary.isError || !summary.data) return <LoadFailed onRetry={() => summary.refetch()} />;

  const trend = summary.data.monthly_cashflow_trend ?? [];

  if (trend.length < MIN_SEASONALITY_MONTHS) {
    return (
      <Card title="Seasonality" sub="Recurring monthly patterns">
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
          <Na reason={`Seasonality needs at least ${MIN_SEASONALITY_MONTHS} months of transactions.`} />
          <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>
            Seasonality needs at least <b>{MIN_SEASONALITY_MONTHS} months</b> of transactions to be meaningful. You have{" "}
            {trend.length} month{trend.length === 1 ? "" : "s"} on this account. Add more history and this will fill in.
          </div>
        </div>
        <Hint style={{ marginTop: 11 }}>
          A pattern drawn from a short period would not be reliable, so nothing is shown until there is enough history.
        </Hint>
      </Card>
    );
  }

  const inflows = trend.map((m) => num(m.inflow) ?? 0);
  const outflows = trend.map((m) => num(m.outflow) ?? 0);
  const peakIn = trend[inflows.indexOf(Math.max(...inflows))];
  const peakOut = trend[outflows.indexOf(Math.max(...outflows))];

  return (
    <Row cols={2}>
      <Card title="Your year has a shape" sub={`Money in, by month · ${trend.length} months of data`}>
        <Spark values={inflows} height={90} />
        <Legend items={trend.map((m) => fmtMonth(m.month))} />
        <div style={{ marginTop: 14, fontSize: 12.5, color: "var(--ink2)" }}>
          Income concentrates in <b>{fmtMonth(peakIn.month)}</b>, which is {(
            (Math.max(...inflows) / (inflows.reduce((a, b) => a + b, 0) / inflows.length)) *
            100
          ).toFixed(0)}
          % of your average month.
        </div>
      </Card>

      <Card title="And so does your spending" sub="Money out, by month">
        <Spark values={outflows} height={90} />
        <Legend items={trend.map((m) => fmtMonth(m.month))} />
        <div style={{ marginTop: 14, fontSize: 12.5, color: "var(--ink2)" }}>
          Spending is heaviest in <b>{fmtMonth(peakOut.month)}</b>.{" "}
          {peakIn.month === peakOut.month
            ? "Your heaviest earning and heaviest spending fall in the same month."
            : "Your heaviest spending month is not your heaviest earning month, which is where a balance gets thin."}
        </div>
      </Card>
    </Row>
  );
}
