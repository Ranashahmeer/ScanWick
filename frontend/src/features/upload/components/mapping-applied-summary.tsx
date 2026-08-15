import { Columns3 } from "lucide-react";
import type { MappingAppliedSummary } from "../uploads-api";

// Only rendered when a Data Mapping Layer mapping was actually used for this
// upload (a merchant relying purely on the hardcoded Shopify/WooCommerce/CRM
// maps has no `mapping_applied` at all — nothing to show here, same
// pattern as DisabledFeaturesList only rendering when non-empty).
export function MappingAppliedCard({ summary }: { summary: MappingAppliedSummary | null }) {
  if (!summary) return null;

  const valueRuleEntries = Object.entries(summary.value_rules_applied);

  return (
    <div className="dqr-disabled">
      <h2 className="dqr-disabled-title">How your columns were read</h2>

      <div className="dqr-disabled-row">
        <div className="dqr-disabled-name">
          <Columns3 size={12} strokeWidth={2.4} />
          <strong>{summary.columns_mapped} column{summary.columns_mapped === 1 ? "" : "s"} mapped</strong>
        </div>
        {summary.unmapped_headers.length > 0 ? (
          <p className="dqr-disabled-desc">
            Not used: {summary.unmapped_headers.join(", ")}.
          </p>
        ) : null}
        {valueRuleEntries.length > 0 ? (
          <p className="dqr-disabled-desc">
            {valueRuleEntries
              .map(([field, rule]) => `${field.replace(/_/g, " ")} read as ${rule.replace(/_/g, " ")}`)
              .join("; ")}
            .
          </p>
        ) : null}
      </div>
    </div>
  );
}
