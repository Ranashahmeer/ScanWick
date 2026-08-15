export type ReportsSectionId = "report-library" | "scheduled-reports" | "export-history";

export const sectionGroups = [
  {
    items: [
      { id: "report-library", label: "Report Library" },
      { id: "scheduled-reports", label: "Scheduled Reports" },
      { id: "export-history", label: "Export History" },
    ],
  },
] as const;

export const sectionLabels: Record<ReportsSectionId, string> = Object.fromEntries(
  sectionGroups.flatMap((group) => group.items.map((item) => [item.id, item.label])),
) as Record<ReportsSectionId, string>;
