import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Bar, BarChart, Cell, ResponsiveContainer } from "recharts";
import { Card, PageHead, StatTile } from "@/features/intelligence/components/shared";
import { useScanwickChrome } from "@/features/landing/chrome";
import { ReconciliationReport } from "@/features/reconciliation/components/reconciliation-report";
import { useDashboardRevenue, useDashboardSummary } from "../ecommerce-api";

function delta(changePct: number | null) {
  if (changePct === null) return undefined;
  return { direction: (changePct >= 0 ? "up" : "down") as "up" | "down", label: `${Math.abs(changePct).toFixed(1)}% vs prior period` };
}

export function CommerceDashboardPage({ merchantId }: { merchantId: string }) {
  const { theme, toggleTheme } = useScanwickChrome();
  const summary = useDashboardSummary(merchantId);
  const revenue = useDashboardRevenue(merchantId);
  const [showReconciliation, setShowReconciliation] = useState(false);

  const summaryData = summary.data;
  const revenueData = revenue.data;

  const gapSeries = revenueData?.monthly_trend.map((row) => ({
    month: row.month,
    value: Number(row.gross) - Number(row.net),
  }));

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
        <PageHead module="Commerce" breadcrumb="Commerce Dashboard" title="Commerce Dashboard" />
        {summaryData?._analysisRunId ? (
          <button type="button" className="fi-stat-link" onClick={() => setShowReconciliation(true)}>
            View reconciliation →
          </button>
        ) : null}
      </div>

      {showReconciliation && summaryData?._analysisRunId ? (
        <ReconciliationReport
          theme={theme}
          onToggleTheme={toggleTheme}
          analysisRunId={summaryData._analysisRunId}
          onClose={() => setShowReconciliation(false)}
        />
      ) : null}

      {summaryData?.data_freshness.is_stale ? (
        <div className="dqr-banner dqr-banner-warning fi-row-tight" style={{ marginBottom: 18 }}>
          <AlertTriangle size={16} strokeWidth={2.4} />
          <p>
            <strong>Data may be stale.</strong>{" "}
            {summaryData.data_freshness.last_synced
              ? `Last synced ${new Date(summaryData.data_freshness.last_synced).toLocaleString()}.`
              : "No sync timestamp available."}
          </p>
        </div>
      ) : null}

      {summaryData ? (
        <div className="fi-grid-4">
          <StatTile
            label="Gross revenue"
            value={`${summaryData.gross_revenue.value} ${summaryData.gross_revenue.currency}`}
            delta={delta(summaryData.gross_revenue.change_pct)}
          />
          <StatTile
            label="Net revenue"
            value={`${summaryData.net_revenue.value} ${summaryData.net_revenue.currency}`}
            delta={delta(summaryData.net_revenue.change_pct)}
          />
          <StatTile label="Orders" value={String(summaryData.total_orders)} />
          <StatTile label="Avg order value" value={summaryData.avg_order_value.toLocaleString()} />
        </div>
      ) : summary.isError ? (
        <p className="fi-card-note">Could not load dashboard summary.</p>
      ) : (
        <p className="fi-card-note">Loading…</p>
      )}

      <div className="fi-grid-2">
        <Card title="Gross vs net revenue" hint="monthly trend">
          {revenueData ? (
            revenueData.monthly_trend.length === 0 ? (
              <p className="fi-card-note">No order history yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height={156}>
                <BarChart data={revenueData.monthly_trend.map((row) => ({ month: row.month, value: Number(row.gross) }))}>
                  <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                    {revenueData.monthly_trend.map((row, index) => (
                      <Cell key={row.month} fill={index === revenueData.monthly_trend.length - 1 ? "#7fc7a3" : "rgba(127,199,163,.46)"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )
          ) : revenue.isError ? (
            <p className="fi-card-note">Could not load.</p>
          ) : (
            <p className="fi-card-note">Loading…</p>
          )}
        </Card>

        <Card title="Revenue gap" hint="gross − net, by month">
          {gapSeries ? (
            gapSeries.length === 0 ? (
              <p className="fi-card-note">No order history yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height={156}>
                <BarChart data={gapSeries}>
                  <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                    {gapSeries.map((row) => (
                      <Cell key={row.month} fill="#ef6262" />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )
          ) : revenue.isError ? (
            <p className="fi-card-note">Could not load.</p>
          ) : (
            <p className="fi-card-note">Loading…</p>
          )}
        </Card>
      </div>

      {revenueData ? (
        <Card title="Where the gap comes from" hint="gross − net breakdown">
          <div className="fi-item-list">
            {Object.entries(revenueData.gap_breakdown).map(([label, value]) => (
              <div className="fi-item-row" key={label}>
                <span className="fi-item-name" style={{ textTransform: "capitalize" }}>{label.replace(/_/g, " ")}</span>
                <span className="fi-item-meta">
                  <span className="fi-item-value">{value}</span>
                </span>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  );
}
