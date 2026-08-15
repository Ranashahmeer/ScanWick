import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { BarList, Card, PageHead, ProgressBar } from "@/features/intelligence/components/shared";
import { useCashflowAnalysis, useLoanReadiness } from "../bank-api";

export function CashflowAnalysisPage({ accountId }: { accountId: string }) {
  const query = useCashflowAnalysis(accountId);
  const loanReadiness = useLoanReadiness(accountId);
  const data = query.data;

  const businessPct = data
    ? (() => {
        const business = data.business_vs_personal.find((row) => row.category.toLowerCase() === "business");
        const total = data.business_vs_personal.reduce((sum, row) => sum + Number(row.total_amount), 0);
        return total > 0 && business ? (Number(business.total_amount) / total) * 100 : null;
      })()
    : null;

  return (
    <div>
      <PageHead
        module="Finance"
        breadcrumb="Cashflow Analysis"
        title="Cashflow Analysis"
        description="Where money goes, what's committed, and how long your buffer lasts."
      />

      {!data ? (
        query.isError ? (
          <p className="fi-card-note">Could not load cashflow analysis.</p>
        ) : (
          <p className="fi-card-note">Loading…</p>
        )
      ) : (
        <>
          <div className="fi-grid-3">
            <div className="fi-card fi-stat-tile">
              <span className="fi-stat-label">Cash buffer</span>
              <span className="fi-stat-value">
                {data.cash_buffer_months !== null ? `${data.cash_buffer_months.toFixed(1)} months` : "—"}
              </span>
              {data.cash_buffer_months !== null ? (
                <ProgressBar percent={Math.min(100, (data.cash_buffer_months / 6) * 100)} label="Target: 6 months" />
              ) : null}
            </div>

            <div className="fi-card fi-stat-tile">
              <span className="fi-stat-label">Expense concentration</span>
              <span className="fi-stat-value">
                {data.expense_concentration_ratio_pct !== null ? `${data.expense_concentration_ratio_pct.toFixed(0)}%` : "—"}
              </span>
              <span className="fi-card-hint" style={{ marginTop: 2 }}>Top-3 payees as % of outflows</span>
            </div>

            <div className="fi-card fi-stat-tile">
              <span className="fi-stat-label">Recurring vs variable</span>
              <span className="fi-stat-value">
                {data.recurring_vs_variable.recurring_pct !== null ? `${data.recurring_vs_variable.recurring_pct.toFixed(0)}%` : "—"}
              </span>
              <span className="fi-card-hint" style={{ marginTop: 2 }}>recurring share of outflows</span>
            </div>
          </div>

          <div className="fi-grid-2">
            <Card title="Recurring vs variable outflows">
              <div className="fi-item-list">
                <div className="fi-item-row">
                  <span className="fi-item-name">Recurring</span>
                  <span className="fi-item-meta"><span className="fi-item-value">{data.recurring_vs_variable.recurring_total}</span></span>
                </div>
                <div className="fi-item-row">
                  <span className="fi-item-name">Variable</span>
                  <span className="fi-item-meta"><span className="fi-item-value">{data.recurring_vs_variable.variable_total}</span></span>
                </div>
              </div>
              <p className="fi-card-note">
                Recurring = same payee ≥3× at similar amounts (±15%) on a 25–35, 8–9, or 85–95-day
                cadence.
              </p>
            </Card>

            <Card title="Business vs personal">
              {businessPct !== null ? (
                <div className="fi-donut-wrap">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.business_vs_personal.map((row) => ({ name: row.category, value: Number(row.total_amount) }))}
                        dataKey="value"
                        innerRadius={62}
                        outerRadius={82}
                        paddingAngle={0}
                        stroke="none"
                      >
                        {data.business_vs_personal.map((row) => (
                          <Cell
                            key={row.category}
                            fill={row.category.toLowerCase() === "business" ? "#7fc7a3" : "rgba(148,163,184,0.28)"}
                          />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="fi-donut-center">
                    <strong>{businessPct.toFixed(0)}%</strong>
                    <span>business</span>
                  </div>
                </div>
              ) : (
                <p className="fi-card-note">No categorized outflows yet.</p>
              )}
            </Card>
          </div>

          <div className="fi-grid-2">
            <Card title="Payment mode breakdown">
              {data.by_payment_mode.length === 0 ? (
                <p className="fi-card-note">No outflows yet.</p>
              ) : (
                <BarList
                  items={(() => {
                    const total = data.by_payment_mode.reduce((sum, row) => sum + Number(row.total_amount), 0);
                    return data.by_payment_mode.map((row) => ({
                      label: row.mode.replace(/_/g, " "),
                      value: row.total_amount,
                      percent: total > 0 ? (Number(row.total_amount) / total) * 100 : 0,
                    }));
                  })()}
                />
              )}
            </Card>

            <Card title="Estimated debt coverage" hint="aggregate estimate, not itemized by loan">
              {loanReadiness.data ? (
                <div className="fi-item-list">
                  <div className="fi-item-row">
                    <span className="fi-item-name">Est. available income</span>
                    <span className="fi-item-meta"><span className="fi-item-value">{loanReadiness.data.estimated_debt_coverage_indicator.estimated_available_income}</span></span>
                  </div>
                  <div className="fi-item-row">
                    <span className="fi-item-name">Est. monthly debt obligations</span>
                    <span className="fi-item-meta"><span className="fi-item-value">{loanReadiness.data.estimated_debt_coverage_indicator.estimated_monthly_debt_obligations}</span></span>
                  </div>
                  <div className="fi-item-row">
                    <span className="fi-item-name">Coverage ratio</span>
                    <span className="fi-item-meta">
                      <span className="fi-item-value">
                        {loanReadiness.data.estimated_debt_coverage_indicator.coverage_ratio !== null
                          ? loanReadiness.data.estimated_debt_coverage_indicator.coverage_ratio.toFixed(2)
                          : "—"}
                      </span>
                    </span>
                  </div>
                  <p className="fi-card-note">{loanReadiness.data.estimated_debt_coverage_indicator.methodology_note}</p>
                </div>
              ) : (
                <p className="fi-card-note">Loading…</p>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
