import { Card, PageHead } from "@/features/intelligence/components/shared";
import { RiskGauge } from "../components/gauge";
import { useFraudRisk, type FraudFlag } from "../bank-api";

const integrityLabel: Record<string, string> = {
  balance_check: "Balance integrity",
  date_continuity: "Date continuity",
  sequential_ordering: "Sequential ordering",
};

function statusBadge(status: string) {
  if (status === "passed") return { className: "dqr-check-badge-pass", label: "Pass" };
  if (status === "failed") return { className: "dqr-check-badge-fail", label: "Flag" };
  return { className: "", label: "Not checked" };
}

function flagDescription(flag: FraudFlag): string {
  if (flag.description) return flag.description;
  // Redacted for loan_officer/bank_viewer roles — description is dropped
  // server-side, so synthesize a generic one from what's still present.
  switch (flag.flag_type) {
    case "z_score_anomaly":
      return `Unusual transaction amount detected (z-score ${flag.z_score ?? "—"}).`;
    case "structuring":
      return `${flag.affected_transaction_count ?? "Multiple"} transactions show a structuring pattern.`;
    case "duplicate_payee":
      return `Duplicate payee detected.`;
    case "timing_anomaly":
      return `Unusual transaction timing detected.`;
    default:
      return "Flagged for review.";
  }
}

export function FraudRiskPage({ accountId }: { accountId: string }) {
  const query = useFraudRisk(accountId);
  const data = query.data;

  return (
    <div>
      <PageHead
        module="Finance"
        breadcrumb="Fraud Risk"
        title="Fraud Risk Score"
        description="Statement-integrity and anomaly checks, explained in plain language."
      />

      {!data ? (
        query.isError ? (
          <p className="fi-card-note">Could not load fraud risk.</p>
        ) : (
          <p className="fi-card-note">Loading…</p>
        )
      ) : (
        <>
          <div className="fi-grid-2">
            <Card title="Fraud risk">
              <RiskGauge score={data.fraud_risk_score} />
              <p className="fi-card-note" style={{ textTransform: "capitalize" }}>Risk level: {data.risk_level}</p>
            </Card>

            <div style={{ display: "grid", gap: 18 }}>
              <Card title="Statement integrity checks">
                <div className="dqr-checks-list">
                  {(["balance_check", "date_continuity", "sequential_ordering"] as const).map((key) => {
                    const badge = statusBadge(data.statement_integrity[key]);
                    return (
                      <div className="dqr-check-row" key={key}>
                        <span>{integrityLabel[key]}</span>
                        <span className={`dqr-check-badge ${badge.className}`}>{badge.label}</span>
                      </div>
                    );
                  })}
                </div>
              </Card>

              <Card title="Score weighting" hint="how each signal contributes">
                <div className="fi-item-list">
                  {Object.entries(data.score_breakdown).map(([label, weight]) => (
                    <div className="fi-item-row" key={label}>
                      <span className="fi-item-name" style={{ textTransform: "capitalize" }}>{label.replace(/_weight$/, "").replace(/_/g, " ")}</span>
                      <span className="fi-item-meta"><span className="fi-item-value">{(weight * 100).toFixed(0)}%</span></span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>

          <div className="fi-row">
            <Card title="Fraud flags">
              {data.flags.length === 0 ? (
                <p className="fi-card-note">No fraud flags on this statement.</p>
              ) : (
                <div className="fi-flag-list">
                  {data.flags.map((flag, index) => (
                    <div className="fi-flag-card" key={`${flag.flag_type}-${index}`}>
                      <div className="fi-flag-head">
                        <span className={`fi-flag-badge fi-flag-badge-${flag.severity}`}>{flag.severity}</span>
                        <strong style={{ textTransform: "capitalize" }}>{flag.flag_type.replace(/_/g, " ")}</strong>
                      </div>
                      <p className="fi-flag-desc">{flagDescription(flag)}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
