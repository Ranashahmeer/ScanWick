import { useState } from "react";
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, XAxis } from "recharts";
import { Card, ItemList, Legend, PageHead, StatTile } from "@/features/intelligence/components/shared";
import { useScanwickChrome } from "@/features/landing/chrome";
import { ReconciliationReport } from "@/features/reconciliation/components/reconciliation-report";
import { useDashboardSummary, useLoanReadiness } from "../bank-api";

export function FinancialSummaryPage({
  accountId,
  onViewLoanReadiness,
}: {
  accountId: string;
  onViewLoanReadiness: () => void;
}) {
  const { theme, toggleTheme } = useScanwickChrome();
  const summary = useDashboardSummary(accountId);
  const loanReadiness = useLoanReadiness(accountId);
  const data = summary.data;
  const [showReconciliation, setShowReconciliation] = useState(false);

  const creditCount = data?.credit_debit_split.credit_count ?? 0;
  const debitCount = data?.credit_debit_split.debit_count ?? 0;
  const totalTransactions = creditCount + debitCount;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
        <PageHead module="Finance" breadcrumb="Financial Summary" title="Financial Summary" />
        {data?._analysisRunId ? (
          <button type="button" className="fi-stat-link" onClick={() => setShowReconciliation(true)}>
            View reconciliation →
          </button>
        ) : null}
      </div>

      {showReconciliation && data?._analysisRunId ? (
        <ReconciliationReport
          theme={theme}
          onToggleTheme={toggleTheme}
          analysisRunId={data._analysisRunId}
          onClose={() => setShowReconciliation(false)}
        />
      ) : null}

      {!data ? (
        summary.isError ? (
          <p className="fi-card-note">Could not load the financial summary.</p>
        ) : (
          <p className="fi-card-note">Loading…</p>
        )
      ) : (
        <>
          <div className="fi-grid-2">
            <div className="fi-card fi-score-card">
              {loanReadiness.data ? (
                <>
                  <span className="fi-score-grade">
                    {loanReadiness.data.creditworthiness_tier} <span>{loanReadiness.data.loan_readiness_score}/100</span>
                  </span>
                  <div className="fi-score-copy">
                    <p>
                      Loan Readiness — {loanReadiness.data.tier_definition}.{" "}
                      <a href="#loan-readiness" onClick={(event) => { event.preventDefault(); onViewLoanReadiness(); }}>
                        View →
                      </a>
                    </p>
                  </div>
                </>
              ) : (
                <p className="fi-card-note">Loan readiness score loading…</p>
              )}
            </div>

            <div className="fi-card">
              <div className="fi-verified-head">
                <span>Balance</span>
              </div>
              <p className="fi-verified-note">
                {data.balance.opening ?? "—"} opening → {data.balance.closing ?? "—"} closing
                {data.balance.net_change !== null ? ` (net ${data.balance.net_change})` : ""}
              </p>
            </div>
          </div>

          <div className="fi-grid-4">
            <StatTile label="Total inflows" value={data.inflows} />
            <StatTile label="Total outflows" value={data.outflows} />
            <StatTile
              label="Net cash position"
              value={data.balance.net_change ?? "—"}
            />
            <StatTile label="Transactions" value={totalTransactions.toLocaleString()} />
          </div>

          <div className="fi-grid-2">
            <Card title="Monthly inflows vs outflows">
              {data.monthly_cashflow_trend.length === 0 ? (
                <p className="fi-card-note">No transaction history yet.</p>
              ) : (
                <>
                  <ResponsiveContainer width="100%" height={190}>
                    <BarChart
                      data={data.monthly_cashflow_trend.map((row) => ({
                        month: row.month,
                        inflow: Number(row.inflow),
                        outflow: Number(row.outflow),
                      }))}
                      barGap={4}
                      barCategoryGap="30%"
                    >
                      <XAxis dataKey="month" stroke="rgba(148,163,184,0.6)" fontSize={11} tickLine={false} axisLine={false} />
                      <Bar dataKey="inflow" fill="#7fc7a3" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="outflow" fill="rgba(148,163,184,0.55)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                  <Legend
                    items={[
                      { label: "Inflows", color: "#7fc7a3" },
                      { label: "Outflows", color: "rgba(148,163,184,0.55)" },
                    ]}
                  />
                </>
              )}
            </Card>

            <Card title="Credit vs debit" hint="by transaction count">
              <div className="fi-donut-wrap">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={[
                        { name: "Credit", value: data.credit_debit_split.credit_pct },
                        { name: "Debit", value: data.credit_debit_split.debit_pct },
                      ]}
                      dataKey="value"
                      innerRadius={62}
                      outerRadius={82}
                      paddingAngle={0}
                      stroke="none"
                    >
                      <Cell fill="#7fc7a3" />
                      <Cell fill="rgba(148,163,184,0.28)" />
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="fi-donut-center">
                  <strong>{data.credit_debit_split.credit_pct.toFixed(0)}%</strong>
                  <span>credit</span>
                </div>
              </div>
            </Card>
          </div>

          <div className="fi-grid-2">
            <Card title="Top payees by outflow">
              {data.top_payees_by_outflow.length === 0 ? (
                <p className="fi-card-note">No outflows yet.</p>
              ) : (
                <ItemList
                  items={data.top_payees_by_outflow.map((row) => ({
                    name: row.payee,
                    value: row.total_outflow,
                    pct: `${row.occurrence_count}x`,
                  }))}
                />
              )}
            </Card>

            <Card title="Top income sources">
              {data.top_income_sources.length === 0 ? (
                <p className="fi-card-note">No inflows yet.</p>
              ) : (
                <ItemList
                  items={data.top_income_sources.map((row) => ({
                    name: row.payee,
                    value: row.total_inflow,
                    pct: `${row.occurrence_count}x`,
                  }))}
                />
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
