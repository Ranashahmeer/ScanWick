import { Bar, BarChart, ResponsiveContainer, XAxis } from "recharts";
import { Card, LockedPageState, PageHead } from "@/features/intelligence/components/shared";
import { useDashboardSummary, useIncomeStability } from "../bank-api";

const labelTone: Record<string, string> = {
  stable: "#7fc7a3",
  moderate: "#f0b060",
  volatile: "#f06060",
};

export function IncomeStabilityPage({ accountId }: { accountId: string }) {
  const query = useIncomeStability(accountId);
  const summary = useDashboardSummary(accountId);
  const envelope = query.data;
  const data = envelope?.data ?? null;

  return (
    <div>
      <PageHead
        module="Finance"
        breadcrumb="Income Stability"
        title="Income Stability"
        description="How consistent your inflows are, month to month."
      />

      {query.isLoading ? (
        <p className="fi-card-note">Loading…</p>
      ) : query.isError ? (
        <p className="fi-card-note">Could not load income stability.</p>
      ) : data === null ? (
        <div className="fi-row-tight" style={{ marginTop: 18 }}>
          <LockedPageState
            title="Not enough history yet"
            description={
              envelope?.meta.disabled_features[0]?.reason ??
              "Income Stability needs at least 3 months of transaction data."
            }
          />
        </div>
      ) : (
        <>
          <div className="fi-grid-2">
            <Card title="Monthly inflows">
              {summary.data && summary.data.monthly_cashflow_trend.length > 0 ? (
                <ResponsiveContainer width="100%" height={210}>
                  <BarChart
                    data={summary.data.monthly_cashflow_trend.map((row) => ({ month: row.month, value: Number(row.inflow) }))}
                    barCategoryGap="35%"
                  >
                    <XAxis dataKey="month" stroke="rgba(148,163,184,0.6)" fontSize={11} tickLine={false} axisLine={false} />
                    <Bar dataKey="value" fill="#2a9d6f" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="fi-card-note">No inflow history yet.</p>
              )}
            </Card>

            <Card title="Coefficient of variation">
              <div style={{ display: "grid", gap: 6 }}>
                <span className="fi-stat-value" style={{ fontSize: 30, color: labelTone[data.label] }}>
                  {data.cv_pct.toFixed(0)}%
                </span>
                <span className="fi-stat-delta fi-stat-delta-up" style={{ textTransform: "capitalize" }}>{data.label}</span>
              </div>
              <div className="fi-legend" style={{ marginTop: 14 }}>
                <span className="fi-legend-item">
                  <span className="fi-legend-dot" style={{ background: "#7fc7a3" }} />
                  Stable &lt;20%
                </span>
                <span className="fi-legend-item">
                  <span className="fi-legend-dot" style={{ background: "#f0b060" }} />
                  Moderate 20–40%
                </span>
                <span className="fi-legend-item">
                  <span className="fi-legend-dot" style={{ background: "#f06060" }} />
                  Volatile &gt;40%
                </span>
              </div>
              <p className="fi-card-note">
                Score: {data.score}/100. CV = standard deviation ÷ mean of monthly inflows. Lower is
                steadier income — lenders prefer it.
              </p>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
