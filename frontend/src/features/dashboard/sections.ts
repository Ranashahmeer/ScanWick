export type SectionId =
  | "financial-summary"
  | "income-stability"
  | "avg-monthly-balance"
  | "cashflow"
  | "fraud-risk"
  | "loan-readiness"
  | "90-day-forecast"
  | "lender-brief"
  | "health-playbook";

export interface SectionConfig {
  id: SectionId;
  label: string;
  // Matches a key in backend/app/services/plan_permissions.py — looked up
  // against the plan permissions matrix (usePlanPermissions()) to decide
  // whether a section is locked for the caller's current tier. Empty
  // string means "no matrix row" (e.g. avg-monthly-balance, not part of
  // the PDF matrix) — always treated as accessible.
  featureKey: string;
}

export interface SectionGroup {
  items: SectionConfig[];
}

// statement-integrity was removed here — its only data (statement_integrity)
// already ships as a sub-object of predictive/fraud-risk, and is shown on
// the Fraud Risk page; a standalone page would just be a duplicate slice of
// the same endpoint. See docs/INTEGRATION_PLAN.md Phase 6.
export const sectionGroups: SectionGroup[] = [
  {
    items: [
      { id: "financial-summary", label: "Financial Summary", featureKey: "bank.dashboard_summary" },
      { id: "income-stability", label: "Income Stability", featureKey: "bank.income_stability" },
      { id: "avg-monthly-balance", label: "Avg Monthly Balance", featureKey: "" },
      { id: "cashflow", label: "Cashflow", featureKey: "bank.cashflow_analysis" },
      { id: "fraud-risk", label: "Fraud Risk", featureKey: "bank.fraud_risk" },
    ],
  },
  {
    items: [
      { id: "loan-readiness", label: "Loan Readiness", featureKey: "bank.loan_readiness" },
      { id: "90-day-forecast", label: "90-Day Forecast", featureKey: "bank.cashflow_forecast" },
      { id: "lender-brief", label: "Lender Brief", featureKey: "bank.lender_brief" },
      { id: "health-playbook", label: "Health Playbook", featureKey: "bank.financial_health_playbook" },
    ],
  },
];

export const sectionLabels: Record<SectionId, string> = Object.fromEntries(
  sectionGroups.flatMap((group) => group.items.map((item) => [item.id, item.label])),
) as Record<SectionId, string>;

export const sectionFeatureKeys: Record<SectionId, string> = Object.fromEntries(
  sectionGroups.flatMap((group) => group.items.map((item) => [item.id, item.featureKey])),
) as Record<SectionId, string>;
