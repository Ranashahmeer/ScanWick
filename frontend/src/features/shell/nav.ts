/**
 * Application navigation.
 *
 * Groups and ordering follow the prototype's own structure — Individual
 * (Surface 1), Ingestion, Account connection, Audit, Lending (Surface 2),
 * Monitoring (Surface 3), Consent & Institution, Account. The two-digit
 * mark on each item is the prototype's screen number, kept because the
 * sidebar renders it and because it is how the design is referred to.
 *
 * `surface` decides who sees a group: an individual never sees the lending
 * or monitoring surfaces, and an institutional user never sees the personal
 * money screens. Both see account/consent.
 */

export type Surface = "individual" | "institution" | "both";

export interface NavItem {
  /** Prototype screen number, rendered in the sidebar rail. */
  n: string;
  label: string;
  to: string;
  /** Sub-screen selector for pages that host several prototype screens. */
  search?: Record<string, string>;
}

export interface NavGroup {
  title: string;
  surface: Surface;
  items: NavItem[];
}

export const navGroups: NavGroup[] = [
  {
    title: "Your money",
    surface: "individual",
    items: [
      { n: "17", label: "Home", to: "/dashboard" },
      { n: "18", label: "Consolidated view", to: "/money", search: { view: "consolidated" } },
      { n: "19", label: "Coverage statement", to: "/money", search: { view: "coverage" } },
      { n: "20", label: "Where money goes", to: "/money", search: { view: "spending" } },
      { n: "21", label: "Top payees", to: "/money", search: { view: "payees" } },
      { n: "22", label: "Recurring outflows", to: "/money", search: { view: "recurring" } },
      { n: "23", label: "Fees & charges", to: "/money", search: { view: "fees" } },
      { n: "24", label: "Income & patterns", to: "/money", search: { view: "income" } },
      { n: "64", label: "Income stability", to: "/money", search: { view: "stability" } },
      { n: "25", label: "Seasonality", to: "/money", search: { view: "seasonality" } },
      { n: "26", label: "Business vs personal", to: "/money", search: { view: "classify" } },
      { n: "27", label: "Balance behaviour", to: "/money", search: { view: "balance" } },
      { n: "29", label: "Obligations & ajo", to: "/money", search: { view: "obligations" } },
      { n: "63", label: "Financial health playbook", to: "/money", search: { view: "playbook" } },
      { n: "30", label: "My readiness", to: "/money", search: { view: "readiness" } },
      { n: "31", label: "Export", to: "/reports" },
    ],
  },
  {
    title: "Accounts",
    surface: "both",
    items: [
      { n: "06", label: "Add accounts", to: "/accounts" },
      { n: "07", label: "Upload statement", to: "/upload" },
      { n: "15", label: "Connection health", to: "/accounts", search: { view: "health" } },
    ],
  },
  {
    title: "Audit",
    surface: "both",
    items: [
      { n: "32", label: "Account audit", to: "/audit" },
      { n: "33", label: "Who looked at your data", to: "/audit", search: { view: "access-trail" } },
      { n: "61", label: "Analysis run record", to: "/audit", search: { view: "run-record" } },
    ],
  },
  {
    title: "Lending",
    surface: "institution",
    items: [
      { n: "65", label: "Institution home", to: "/lending" },
      { n: "35", label: "Assessments", to: "/lending", search: { view: "assessments" } },
      { n: "36", label: "New assessment", to: "/lending", search: { view: "new" } },
      { n: "37", label: "Signal set", to: "/lending", search: { view: "signals" } },
      { n: "38", label: "Lender brief", to: "/lending", search: { view: "brief" } },
      { n: "39", label: "Traceability", to: "/lending", search: { view: "traceability" } },
      { n: "40", label: "Loan stacking", to: "/lending", search: { view: "stacking" } },
      { n: "41", label: "Borrower type", to: "/lending", search: { view: "type" } },
      { n: "34", label: "Access log", to: "/audit", search: { view: "institution-log" } },
    ],
  },
  {
    title: "Monitoring",
    surface: "institution",
    items: [
      { n: "46", label: "Portfolio", to: "/portfolio" },
      { n: "47", label: "Facility detail", to: "/portfolio", search: { view: "facility" } },
      { n: "48", label: "Signal detail", to: "/portfolio", search: { view: "signal" } },
      { n: "49", label: "Acknowledge", to: "/portfolio", search: { view: "acknowledge" } },
      { n: "50", label: "Notifications", to: "/notifications" },
    ],
  },
  {
    title: "Sharing & consent",
    surface: "both",
    items: [
      { n: "42", label: "Create share link", to: "/shares", search: { view: "create" } },
      { n: "43", label: "Manage shares", to: "/shares" },
      { n: "51", label: "Consent centre", to: "/consent" },
    ],
  },
  {
    title: "Institution",
    surface: "institution",
    items: [
      { n: "53", label: "Team & roles", to: "/institution" },
      { n: "54", label: "Credit ledger", to: "/institution", search: { view: "credits" } },
      { n: "56", label: "API & webhooks", to: "/institution", search: { view: "api" } },
    ],
  },
  {
    title: "Trading records",
    surface: "both",
    items: [
      { n: "58", label: "Connect trading records", to: "/commerce-intelligence" },
      { n: "59", label: "Cash-gap verification", to: "/commerce-intelligence", search: { view: "cash-gap" } },
    ],
  },
  {
    title: "Account",
    surface: "both",
    items: [
      { n: "57", label: "User account", to: "/account" },
      { n: "67", label: "Security & activity", to: "/account", search: { tab: "security" } },
      { n: "66", label: "Billing & payments", to: "/account", search: { tab: "billing" } },
      { n: "55", label: "Plans", to: "/account", search: { tab: "plans" } },
      { n: "68", label: "Delete account", to: "/account", search: { tab: "delete" } },
    ],
  },
];

/**
 * An institutional user is one who holds a non-owner role on a merchant —
 * the same signal team-permissions already uses. Everyone else gets the
 * individual surface, which is also the safe default: the personal money
 * screens are the ones every account can reach.
 */
export function surfaceFor(roles: { role: string }[] | undefined): Exclude<Surface, "both"> {
  const institutional = new Set(["admin", "credit_officer", "portfolio_officer", "viewer"]);
  return roles?.some((r) => institutional.has(r.role)) ? "institution" : "individual";
}

export function groupsForSurface(surface: Exclude<Surface, "both">): NavGroup[] {
  return navGroups.filter((g) => g.surface === "both" || g.surface === surface);
}
