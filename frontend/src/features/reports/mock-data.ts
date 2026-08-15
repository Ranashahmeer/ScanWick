export type ReportModule = "Finance" | "Sales" | "Commerce" | "Cross-module";

export interface ChartPoint {
  label: string;
  value: number;
}

export interface GeneratedReport {
  id: string;
  title: string;
  module: ReportModule;
  period: string;
  generatedAt: string;
  source: string;
  stats: {
    forecastVsActual: string;
    forecastVsActualDelta: string;
    totalSlippage: string;
    confidence: "Low" | "Medium" | "High";
  };
  chart: ChartPoint[];
  note: string;
}

export interface ReportTemplate {
  id: string;
  name: string;
  module: ReportModule;
  description: string;
  lastGenerated: string;
  dateRange: string;
  metrics: string[];
  visualization: "Bar" | "Line" | "Donut" | "Table";
}

export const moduleFilters = ["All", "Finance", "Sales", "Commerce"] as const;

export const libraryTemplates: ReportTemplate[] = [
  {
    id: "tpl-executive-overview",
    name: "Executive Overview",
    module: "Cross-module",
    description: "Cross-module snapshot — finance health, pipeline, and commerce margin on one page.",
    lastGenerated: "2 days ago",
    dateRange: "25 Mar – 17 Jun 2026",
    metrics: ["Finance health", "Pipeline", "Commerce margin"],
    visualization: "Table",
  },
  {
    id: "tpl-monthly-financial-summary",
    name: "Monthly Financial Summary",
    module: "Finance",
    description: "Inflows, outflows, balances, and loan readiness for the period.",
    lastGenerated: "5 days ago",
    dateRange: "1 Jun – 30 Jun 2026",
    metrics: ["Inflows & outflows", "Balances", "Loan readiness"],
    visualization: "Bar",
  },
  {
    id: "tpl-loan-readiness-report",
    name: "Loan Readiness Report",
    module: "Finance",
    description: "Score, factor breakdown, and improvement plan.",
    lastGenerated: "3 weeks ago",
    dateRange: "1 Apr – 30 Jun 2026",
    metrics: ["Loan score", "Factor breakdown", "Improvement plan"],
    visualization: "Table",
  },
  {
    id: "tpl-pipeline-review",
    name: "Pipeline Review",
    module: "Sales",
    description: "Stage funnel, leaderboard, and win/loss for the quarter.",
    lastGenerated: "yesterday",
    dateRange: "1 Apr – 30 Jun 2026",
    metrics: ["Stage funnel", "Leaderboard", "Win/loss"],
    visualization: "Bar",
  },
  {
    id: "tpl-quarter-post-mortem",
    name: "Quarter Post-Mortem",
    module: "Sales",
    description: "Forecast vs actual, slippage, and missed-intervention cost.",
    lastGenerated: "1 week ago",
    dateRange: "1 Apr – 30 Jun 2026",
    metrics: ["Forecast vs actual", "Slippage", "Missed-intervention cost"],
    visualization: "Bar",
  },
  {
    id: "tpl-sales-margin-report",
    name: "Sales & Margin Report",
    module: "Commerce",
    description: "Gross-to-net waterfall, profit leaks, and channel performance.",
    lastGenerated: "today",
    dateRange: "1 Apr – 30 Jun 2026",
    metrics: ["Gross-to-net waterfall", "Profit leaks", "Channel performance"],
    visualization: "Bar",
  },
  {
    id: "tpl-inventory-health",
    name: "Inventory Health",
    module: "Commerce",
    description: "Days of cover, stockout risk, and dead stock.",
    lastGenerated: "today",
    dateRange: "1 Apr – 30 Jun 2026",
    metrics: ["Days of cover", "Stockout risk", "Dead stock"],
    visualization: "Table",
  },
  {
    id: "tpl-rfm-export",
    name: "RFM Export",
    module: "Commerce",
    description: "Six-segment customer breakdown for email sync.",
    lastGenerated: "4 days ago",
    dateRange: "1 Jan – 30 Jun 2026",
    metrics: ["RFM segmentation"],
    visualization: "Donut",
  },
];

export const quarterPostMortem: GeneratedReport = {
  id: "quarter-post-mortem-q2-2026",
  title: "Quarter Post-Mortem — Q2 2026",
  module: "Finance",
  period: "1 Apr – 30 Jun 2026",
  generatedAt: "18 Jun 2026 14:32",
  source: "CRM export + Shopify",
  stats: {
    forecastVsActual: "₦9.1M",
    forecastVsActualDelta: "-7%",
    totalSlippage: "₦3.4M",
    confidence: "Medium",
  },
  chart: [
    { label: "Forecast", value: 9.1 },
    { label: "Actual", value: 8.47 },
  ],
  note: "Forecast confidence is capped at Medium because 2 of 13 weeks in this period rely on interpolated CRM data — this caveat is shown on every export.",
};
