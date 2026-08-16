import { LockedPageState, PageHead } from "@/features/intelligence/components/shared";
import { useAbm } from "../bank-api";

export function AvgMonthlyBalancePage({ accountId }: { accountId: string }) {
  const query = useAbm(accountId);
  const envelope = query.data;
  const data = envelope?.data ?? null;

  return (
    <div>
      <PageHead
        module="Finance"
        breadcrumb="Avg Monthly Balance"
        title="Average Monthly Balance"
        description="ABM is the average of daily closing balances — a truer picture than month-end snapshots."
      />

      {query.isLoading ? (
        <p className="fi-card-note">Loading…</p>
      ) : query.isError ? (
        <p className="fi-card-note">Could not load average monthly balance.</p>
      ) : data === null ? (
        <div className="fi-row-tight" style={{ marginTop: 18 }}>
          <LockedPageState
            title="Not enough balance history"
            description={
              envelope?.meta.disabled_features[0]?.reason ??
              "Not enough daily closing balance data to compute a 3-month and 12-month average."
            }
          />
        </div>
      ) : (
        <>
          <div className="fi-grid-3">
            <div className="fi-card fi-stat-tile">
              <span className="fi-stat-label">ABM · 3-month</span>
              <span className="fi-stat-value sw-num">{data.abm_3m !== null ? `₦${data.abm_3m.toLocaleString()}` : <span className="na">Unavailable</span>}</span>
            </div>

            <div className="fi-card fi-stat-tile">
              <span className="fi-stat-label">ABM · 6-month</span>
              <span className="fi-stat-value sw-num">{data.abm_6m !== null ? `₦${data.abm_6m.toLocaleString()}` : <span className="na">Unavailable</span>}</span>
            </div>

            <div className="fi-card fi-stat-tile">
              <span className="fi-stat-label">ABM · 12-month</span>
              <span className="fi-stat-value sw-num">{data.abm_12m !== null ? `₦${data.abm_12m.toLocaleString()}` : <span className="na">Unavailable</span>}</span>
            </div>
          </div>

          <div className="fi-card fi-row-tight" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "var(--sw-text-solid)" }}>Overall trend</span>
            <span style={{ textTransform: "capitalize", color: data.trend === "improving" ? "#7fc7a3" : data.trend === "declining" ? "#f06060" : undefined }}>
              {data.trend}
            </span>
          </div>

          <p className="fi-card-note" style={{ marginTop: 6 }}>
            Score: {data.score}/100. Methodology: ABM = Σ(daily closing balance) ÷ days in period.
            Transaction-point balances are not used.
          </p>
        </>
      )}
    </div>
  );
}
