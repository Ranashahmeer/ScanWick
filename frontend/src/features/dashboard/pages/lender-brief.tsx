import { Card, PageHead } from "@/features/intelligence/components/shared";
import { useLenderBrief } from "../bank-api";

export function LenderBriefPage({ accountId }: { accountId: string }) {
  const query = useLenderBrief(accountId);
  const data = query.data;

  return (
    <div>
      <PageHead
        module="Finance"
        breadcrumb="Lender Brief"
        title="Lender Brief"
        description="A one-page summary for a lender: business overview, risk, and loan readiness."
      />

      {!data ? (
        query.isError ? (
          <p className="fi-card-note">Could not load the lender brief.</p>
        ) : (
          <p className="fi-card-note">Generating…</p>
        )
      ) : (
        <>
          <div className="fi-card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <h2 className="fi-card-title">
                {data.sections.business_overview.bank_name ?? "Bank statement"} — {data.sections.business_overview.transactions_analyzed} transactions
              </h2>
              <p className="fi-card-note" style={{ marginTop: 4 }}>
                {data.sections.business_overview.statement_period_start ?? "—"} to {data.sections.business_overview.statement_period_end ?? "—"}
              </p>
            </div>
            <a
              href={data.pdf_url}
              target="_blank"
              rel="noreferrer"
              style={{
                flexShrink: 0,
                borderRadius: 8,
                padding: "10px 16px",
                color: "#04140d",
                background: "linear-gradient(180deg, #7fc7a3 0%, #1b7a4b 100%)",
                fontSize: 12.5,
                fontWeight: 750,
                textDecoration: "none",
              }}
            >
              Download PDF
            </a>
          </div>

          <div className="fi-grid-4">
            <div className="fi-card fi-stat-tile">
              <span className="fi-stat-label">Loan readiness</span>
              <span className="fi-stat-value">{data.key_metrics.creditworthiness_tier} · {data.key_metrics.loan_readiness_score}/100</span>
            </div>
            <div className="fi-card fi-stat-tile">
              <span className="fi-stat-label">Fraud risk score</span>
              <span className="fi-stat-value">{data.key_metrics.fraud_risk_score}/100</span>
            </div>
            <div className="fi-card fi-stat-tile">
              <span className="fi-stat-label">Income stability</span>
              <span className="fi-stat-value">{data.key_metrics.income_stability_score ?? "—"}</span>
            </div>
            <div className="fi-card fi-stat-tile">
              <span className="fi-stat-label">Cash buffer</span>
              <span className="fi-stat-value">
                {data.key_metrics.cash_buffer_months !== null ? `${data.key_metrics.cash_buffer_months.toFixed(1)}mo` : "—"}
              </span>
            </div>
          </div>

          {data.sections.lender_recommendation.length > 0 ? (
            <div className="fi-row">
              <Card title="Recommendation">
                {data.sections.lender_recommendation.map((rec) => (
                  <p className="fi-card-note" key={rec.id} style={{ marginTop: 0 }}>
                    <strong style={{ color: "var(--sw-text-solid)" }}>{rec.recommended_action}</strong> — {rec.reasoning}
                  </p>
                ))}
              </Card>
            </div>
          ) : null}

          <p className="fi-card-note">{data.data_source_footnote}</p>
        </>
      )}
    </div>
  );
}
