import { useState } from "react";
import { FileText, Plus } from "lucide-react";
import { Badge, PageHead } from "@/features/intelligence/components/shared";
import { CreateReportPage } from "./create-report";
import { ReportViewerPage } from "./report-viewer";
import { libraryTemplates, moduleFilters, quarterPostMortem, type GeneratedReport, type ReportTemplate } from "../mock-data";

type View = "list" | "create" | "viewer";

export function ReportLibraryPage() {
  const [view, setView] = useState<View>("list");
  const [templates, setTemplates] = useState<ReportTemplate[]>(libraryTemplates);
  const [moduleFilter, setModuleFilter] = useState<(typeof moduleFilters)[number]>("All");
  const [activeReport, setActiveReport] = useState<GeneratedReport | null>(null);

  const filtered = templates.filter((template) => moduleFilter === "All" || template.module === moduleFilter);

  const openReport = (report: GeneratedReport) => {
    setActiveReport(report);
    setView("viewer");
  };

  if (view === "create") {
    return (
      <CreateReportPage
        onCancel={() => setView("list")}
        onSaveTemplate={(template) => {
          setTemplates((current) => [template, ...current]);
          setView("list");
        }}
        onGenerate={(report) => openReport(report)}
      />
    );
  }

  if (view === "viewer" && activeReport) {
    return <ReportViewerPage report={activeReport} onBack={() => setView("list")} />;
  }

  return (
    <div>
      <div className="rpt-page-head-row">
        <PageHead
          module="Reports"
          breadcrumb="Report Library"
          title="Report Library"
          description="Pre-built templates — generate on demand or schedule them."
        />
        <div className="rpt-actions-row">
          <button type="button" className="rpt-btn rpt-btn-primary" onClick={() => setView("create")}>
            <Plus size={14} strokeWidth={2.6} /> Create report
          </button>
        </div>
      </div>

      <div className="fi-chip-row" style={{ marginTop: 18 }}>
        {moduleFilters.map((label) => (
          <button
            type="button"
            key={label}
            className={`fi-chip ${moduleFilter === label ? "fi-chip-active" : ""}`}
            onClick={() => setModuleFilter(label)}
          >
            {label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="fi-empty fi-row-tight">
          <span className="fi-empty-icon">
            <FileText size={18} strokeWidth={2.2} />
          </span>
          <h3>No templates in this module yet</h3>
          <p>Create a custom report and save it as a template to see it here.</p>
          <button type="button" className="rpt-btn rpt-btn-primary" onClick={() => setView("create")}>
            Create report
          </button>
        </div>
      ) : (
        <div className="rpt-template-grid">
          {filtered.map((template) => (
            <div className="fi-card rpt-template-card" key={template.id}>
              <Badge tone={template.module === "Cross-module" ? "neutral" : "success"}>{template.module}</Badge>
              <h3 className="rpt-template-card-title">{template.name}</h3>
              <p className="rpt-template-card-desc">{template.description}</p>
              <p className="rpt-template-card-meta">Last generated {template.lastGenerated}</p>
              <button
                type="button"
                className="rpt-btn rpt-btn-primary rpt-btn-block"
                onClick={() =>
                  openReport({
                    id: `${template.id}-${Date.now()}`,
                    title: template.name,
                    module: template.module,
                    period: template.dateRange,
                    generatedAt: "just now",
                    source: "live data",
                    stats: quarterPostMortem.stats,
                    chart: quarterPostMortem.chart,
                    note: `Generated from the "${template.name}" template · metrics: ${template.metrics.join(", ") || "none selected"}.`,
                  })
                }
              >
                Generate
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
