import { Area, ComposedChart, Line, ResponsiveContainer, XAxis } from "recharts";
import { Card, PageHead, StatTile } from "@/features/intelligence/components/shared";
import { useCashflowForecast } from "../bank-api";

export function CashflowForecastPage({ accountId }: { accountId: string }) {
  const query = useCashflowForecast(accountId);
  const data = query.data;

  return (
    <div>
      <PageHead
        module="Finance"
        breadcrumb="90-Day Forecast"
        title="90-Day Cashflow Forecast"
        description="Projected daily balance, with an 80% confidence band, plus a stress scenario at 20% lower income."
      />

      {!data ? (
        query.isError ? (
          <p className="fi-card-note">Could not load the cashflow forecast.</p>
        ) : (
          <p className="fi-card-note">Loading…</p>
        )
      ) : (
        <>
          <div className="fi-grid-2">
            <StatTile
              label="Cash runway (primary)"
              value={data.cash_runway.primary_scenario_months !== null ? `${data.cash_runway.primary_scenario_months.toFixed(1)} months` : "Cash positive"}
            />
            <StatTile
              label="Cash runway (stress)"
              value={data.cash_runway.stress_scenario_months !== null ? `${data.cash_runway.stress_scenario_months.toFixed(1)} months` : "Cash positive"}
              delta={{ direction: "down", label: data.cash_runway.stress_assumption }}
            />
          </div>

          <div className="fi-row">
            <Card title="Projected balance" hint={`${data.forecast_days} days from ${data.base_date}`}>
              <ResponsiveContainer width="100%" height={220}>
                <ComposedChart data={data.daily_forecast.map((row) => ({
                  date: row.date,
                  balance: Number(row.projected_balance),
                  lower: Number(row.confidence_lower_80),
                  upper: Number(row.confidence_upper_80),
                }))}>
                  <XAxis dataKey="date" stroke="rgba(148,163,184,0.6)" fontSize={10} tickLine={false} axisLine={false} interval={13} />
                  <Area dataKey={(row: { lower: number; upper: number }) => [row.lower, row.upper]} stroke="none" fill="rgba(61,220,132,0.15)" />
                  <Line type="monotone" dataKey="balance" stroke="#7fc7a3" strokeWidth={2} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {data.recurring_commitments_projected.length > 0 ? (
            <div className="fi-row">
              <Card title="Recurring commitments projected into this window">
                <div className="fi-item-list">
                  {data.recurring_commitments_projected.map((row, index) => (
                    <div className="fi-item-row" key={`${row.payee}-${index}`}>
                      <span className="fi-item-name">{row.payee}</span>
                      <span className="fi-item-meta">
                        <span className="fi-item-value">{row.amount}</span>
                        <span className="fi-item-pct">{row.expected_dates.length}x</span>
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
