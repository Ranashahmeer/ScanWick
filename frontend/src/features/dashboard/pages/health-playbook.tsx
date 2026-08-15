import type { ReactNode } from "react";
import { Badge, PageHead } from "@/features/intelligence/components/shared";
import { useFinancialHealthPlaybook } from "../bank-api";

const urgencyLabel: Record<string, string> = {
  this_week: "This week",
  this_month: "This month",
  this_quarter: "This quarter",
};

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "130px 1fr", gap: 12, padding: "8px 0" }}>
      <span style={{ color: "rgba(var(--sw-text-rgb), 0.45)", fontSize: 10.5, fontWeight: 700, textTransform: "uppercase" }}>
        {label}
      </span>
      <div style={{ color: "var(--sw-text-solid)", fontSize: 12.5, lineHeight: 1.5 }}>{children}</div>
    </div>
  );
}

export function HealthPlaybookPage({ accountId }: { accountId: string }) {
  const query = useFinancialHealthPlaybook(accountId);
  const recommendations = query.data?.recommendations ?? [];

  return (
    <div>
      <PageHead
        module="Finance"
        breadcrumb="Financial Health Playbook"
        title="Financial Health Playbook"
        description="Specific actions to improve financial health, with reasoning."
      />

      {query.isLoading ? (
        <p className="fi-card-note" style={{ marginTop: 18 }}>Loading recommendations…</p>
      ) : query.isError ? (
        <p className="fi-card-note" style={{ marginTop: 18 }}>Could not load the playbook.</p>
      ) : recommendations.length === 0 ? (
        <p className="fi-card-note" style={{ marginTop: 18 }}>No recommendations right now.</p>
      ) : (
        <div style={{ display: "grid", gap: 16, marginTop: 18 }}>
          {recommendations.map((card) => (
            <div className="fi-card" key={card.id}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                <Badge tone="neutral">{card.entity_type}</Badge>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6, color: "#f0b060", fontSize: 11, fontWeight: 700 }}>
                  <span style={{ width: 7, height: 7, borderRadius: 999, background: "#f0b060", display: "inline-block" }} />
                  {(card.confidence_score * 100).toFixed(0)}% confidence
                </span>
              </div>

              <Field label="Trigger">{card.trigger_condition}</Field>
              <Field label="Entity">{card.entity_name}</Field>
              <Field label="Action">{card.recommended_action}</Field>
              <Field label="Reasoning">
                <span style={{ color: "rgba(var(--sw-text-rgb), 0.62)" }}>{card.reasoning}</span>
              </Field>
              <Field label="Urgency">
                <Badge tone="warning">{urgencyLabel[card.urgency] ?? card.urgency}</Badge>
              </Field>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
