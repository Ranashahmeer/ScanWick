import { Badge, Card, PageHead, Table } from "@/features/intelligence/components/shared";
import { useLoanReadiness } from "../bank-api";

export function LoanReadinessPage({ accountId }: { accountId: string }) {
  const query = useLoanReadiness(accountId);
  const data = query.data;

  return (
    <div>
      <PageHead
        module="Finance"
        breadcrumb="Loan Readiness"
        title="Loan Readiness"
        description="A blended score from income stability, balance trend, fraud risk, and cash buffer — only using whichever of those are computable."
      />

      {!data ? (
        query.isError ? (
          <p className="fi-card-note">Could not load loan readiness.</p>
        ) : (
          <p className="fi-card-note">Loading…</p>
        )
      ) : (
        <>
          <div className="fi-card fi-score-card">
            <span className="fi-score-grade">
              {data.creditworthiness_tier} <span>{data.loan_readiness_score}/100</span>
            </span>
            <div className="fi-score-copy">
              <p>{data.tier_definition}</p>
            </div>
          </div>

          {data.disabled_components.length > 0 ? (
            <p className="fi-card-note">
              Not included (unavailable): {data.disabled_components.map((c) => c.replace(/_/g, " ")).join(", ")}.
            </p>
          ) : null}

          <div className="fi-row">
            <Card title="Score breakdown">
              {Object.keys(data.score_breakdown).length === 0 ? (
                <p className="fi-card-note">No components available to score.</p>
              ) : (
                <Table
                  columns={[
                    { key: "factor", label: "Factor" },
                    { key: "weight", label: "Weight", align: "right" },
                    { key: "score", label: "Score", align: "right" },
                    { key: "contribution", label: "Contribution", align: "right" },
                  ]}
                  rows={Object.entries(data.score_breakdown).map(([factor, breakdown]) => ({
                    factor: factor.replace(/_/g, " "),
                    weight: `${breakdown.weight_pct}%`,
                    score: breakdown.score,
                    contribution: breakdown.contribution,
                  }))}
                  rowKey={(row) => row.factor as string}
                />
              )}
            </Card>
          </div>

          {data.improvement_recommendations.length > 0 ? (
            <div className="fi-row">
              <Card title="How to improve your score">
                <Table
                  columns={[
                    { key: "factor", label: "Factor" },
                    { key: "current", label: "Current", align: "right" },
                    { key: "target", label: "Target", align: "right" },
                    { key: "action", label: "Action", width: "2fr" },
                    { key: "gain", label: "Est. gain", align: "right" },
                  ]}
                  rows={data.improvement_recommendations.map((rec) => ({
                    factor: rec.factor.replace(/_/g, " "),
                    current: rec.current_value,
                    target: rec.target_value,
                    action: rec.action,
                    gain: <Badge tone="success">+{rec.estimated_score_gain}</Badge>,
                  }))}
                  rowKey={(row) => row.factor as string}
                />
              </Card>
            </div>
          ) : null}

          <div className="fi-row">
            <Card title="Estimated debt coverage">
              <div className="fi-item-list">
                <div className="fi-item-row">
                  <span className="fi-item-name">Est. available income</span>
                  <span className="fi-item-meta"><span className="fi-item-value">{data.estimated_debt_coverage_indicator.estimated_available_income}</span></span>
                </div>
                <div className="fi-item-row">
                  <span className="fi-item-name">Est. monthly debt obligations</span>
                  <span className="fi-item-meta"><span className="fi-item-value">{data.estimated_debt_coverage_indicator.estimated_monthly_debt_obligations}</span></span>
                </div>
                <div className="fi-item-row">
                  <span className="fi-item-name">Coverage ratio</span>
                  <span className="fi-item-meta">
                    <span className="fi-item-value">
                      {data.estimated_debt_coverage_indicator.coverage_ratio !== null
                        ? data.estimated_debt_coverage_indicator.coverage_ratio.toFixed(2)
                        : "—"}
                    </span>
                  </span>
                </div>
              </div>
              <p className="fi-card-note">{data.estimated_debt_coverage_indicator.methodology_note}</p>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
