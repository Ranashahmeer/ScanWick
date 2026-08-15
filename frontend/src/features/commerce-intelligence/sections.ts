export type CommerceSectionId = "commerce-dashboard";

// Section 4: ecommerce depth features (profit-leak detection, unit-margin
// attribution, dead-stock, return forensics, inventory forecast, RFM
// segmentation, churn prediction, ad-kill-switch, AI commerce playbook)
// were cut from the product entirely -- only the dashboard summary/revenue
// surface survives, backing cash-gap reconciliation. featureKey matches a
// key in backend/app/services/plan_permissions.py.
export const sectionGroups = [
  { items: [
    { id: "commerce-dashboard", label: "Commerce Dashboard", featureKey: "ecommerce.dashboard_summary" },
  ] },
] as const;

export const sectionLabels: Record<CommerceSectionId, string> = Object.fromEntries(
  sectionGroups.flatMap((group) => group.items.map((item) => [item.id, item.label])),
) as Record<CommerceSectionId, string>;

export const sectionFeatureKeys: Record<CommerceSectionId, string> = Object.fromEntries(
  sectionGroups.flatMap((group) => group.items.map((item) => [item.id, item.featureKey])),
) as Record<CommerceSectionId, string>;
