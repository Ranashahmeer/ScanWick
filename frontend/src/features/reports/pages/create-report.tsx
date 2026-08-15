import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, XAxis } from "recharts";
import { Card, PageHead, StatTile, Table } from "@/features/intelligence/components/shared";
import type { GeneratedReport, ReportModule, ReportTemplate } from "../mock-data";

const metricOptions = [
  "Gross & net revenue",
  "Revenue-gap waterfall",
  "Profit leak (top 30)",
  "Channel performance",
  "Discount impact",
];

const visualizations = ["Bar", "Line", "Donut", "Table"] as const;
type Visualization = (typeof visualizations)[number];

const previewSeries = [
  { month: "Mar", value: 2.9 },
  { month: "Apr", value: 3.1 },
  { month: "May", value: 3.25 },
  { month: "Jun", value: 3.4 },
];

export function CreateReportPage({
  onCancel,
  onSaveTemplate,
  onGenerate,
}: {
  onCancel: () => void;
  onSaveTemplate: (template: ReportTemplate) => void;
  onGenerate: (report: GeneratedReport) => void;
}) {
  const [name, setName] = useState("Q2 Commerce Margin Review");
  const [module, setModule] = useState<ReportModule>("Commerce");
  const [dateRange, setDateRange] = useState("1 Apr – 30 Jun 2026");
  const [metrics, setMetrics] = useState<string[]>(["Gross & net revenue"]);
  const [visualization, setVisualization] = useState<Visualization>("Bar");

  const toggleMetric = (metric: string) => {
    setMetrics((current) => (current.includes(metric) ? current.filter((item) => item !== metric) : [...current, metric]));
  };

  const template: ReportTemplate = useMemo(
    () => ({
      id: `tpl-${Date.now()}`,
      name,
      module,
      description: metrics.length ? `Custom report tracking ${metrics.join(", ")}.` : "Custom report — no metrics selected yet.",
      lastGenerated: "not yet generated",
      dateRange,
      metrics,
      visualization,
    }),
    [name, module, dateRange, metrics, visualization],
  );

  const handleGenerate = () => {
    onGenerate({
      id: `${template.id}-report`,
      title: name || "Untitled report",
      module,
      period: dateRange,
      generatedAt: "just now",
      source: "live data",
      stats: {
        forecastVsActual: "₦3.40M",
        forecastVsActualDelta: "+7.1%",
        totalSlippage: "₦1.58M",
        confidence: "Medium",
      },
      chart: previewSeries.map((point) => ({ label: point.month, value: point.value })),
      note: `Built from ${metrics.length || "no"} selected metric${metrics.length === 1 ? "" : "s"}: ${metrics.join(", ") || "none"}.`,
    });
  };

  return (
    <div>
      <PageHead
        module="Reports"
        breadcrumb="Create Report"
        title="Create Report"
        description="Pick metrics and a visualization — the preview updates live."
      />

      <div className="rpt-create-grid">
        <Card>
          <label className="acct-field">
            <span>Report name</span>
            <input type="text" value={name} onChange={(event) => setName(event.target.value)} />
          </label>

          <label className="acct-field" style={{ marginTop: 14 }}>
            <span>Module</span>
            <select value={module} onChange={(event) => setModule(event.target.value as ReportModule)}>
              <option value="Finance">Finance</option>
              <option value="Sales">Sales</option>
              <option value="Commerce">Commerce</option>
            </select>
          </label>

          <label className="acct-field" style={{ marginTop: 14 }}>
            <span>Date range</span>
            <input type="text" value={dateRange} onChange={(event) => setDateRange(event.target.value)} />
          </label>

          <p className="fi-stat-label" style={{ marginTop: 16 }}>
            Metrics
          </p>
          <div className="rpt-checkbox-list">
            {metricOptions.map((metric) => (
              <label className="rpt-checkbox-row" key={metric}>
                <input type="checkbox" checked={metrics.includes(metric)} onChange={() => toggleMetric(metric)} />
                {metric}
              </label>
            ))}
          </div>

          <p className="fi-stat-label" style={{ marginTop: 16 }}>
            Visualization
          </p>
          <div className="ci-tabs" style={{ marginTop: 8, marginBottom: 0 }}>
            {visualizations.map((viz) => (
              <button type="button" key={viz} className={visualization === viz ? "active" : ""} onClick={() => setVisualization(viz)}>
                {viz}
              </button>
            ))}
          </div>

          <div className="rpt-form-actions">
            <button type="button" className="rpt-btn rpt-btn-outline" onClick={() => onSaveTemplate(template)}>
              Save as template
            </button>
            <button type="button" className="rpt-btn rpt-btn-primary" onClick={handleGenerate}>
              Generate
            </button>
          </div>
          <button type="button" className="rpt-link" style={{ marginTop: 12 }} onClick={onCancel}>
            ← Back to library
          </button>
        </Card>

        <Card title="Live preview" hint="updates as you edit">
          <p className="rpt-preview-title">{name || "Untitled report"}</p>
          <p className="rpt-preview-meta">
            {dateRange} · {module}
          </p>
          <div className="fi-grid-2" style={{ marginTop: 0, gridTemplateColumns: "1fr 1fr" }}>
            <StatTile label="Gross revenue" value="₦3.40M" />
            <StatTile label="Net revenue" value="₦1.82M" />
          </div>
          <div style={{ marginTop: 18 }}>
            {visualization === "Bar" ? (
              <ResponsiveContainer width="100%" height={170}>
                <BarChart data={previewSeries}>
                  <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                    {previewSeries.map((point, index) => (
                      <Cell key={point.month} fill={index === previewSeries.length - 1 ? "#7fc7a3" : "rgba(127,199,163,.46)"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : null}
            {visualization === "Line" ? (
              <ResponsiveContainer width="100%" height={170}>
                <LineChart data={previewSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(88,145,111,.16)" />
                  <XAxis dataKey="month" tick={{ fontSize: 10 }} stroke="rgba(88,145,111,.3)" />
                  <Line type="monotone" dataKey="value" stroke="#7fc7a3" strokeWidth={2.4} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : null}
            {visualization === "Donut" ? (
              <ResponsiveContainer width="100%" height={170}>
                <PieChart>
                  <Pie data={previewSeries} dataKey="value" nameKey="month" innerRadius={45} outerRadius={70} paddingAngle={2}>
                    {previewSeries.map((point, index) => (
                      <Cell key={point.month} fill={index % 2 === 0 ? "#7fc7a3" : "rgba(127,199,163,.4)"} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            ) : null}
            {visualization === "Table" ? (
              <Table
                columns={[
                  { key: "month", label: "Month" },
                  { key: "value", label: "₦M", align: "right" },
                ]}
                rows={previewSeries.map((point) => ({ month: point.month, value: point.value.toFixed(2) }))}
                rowKey={(row) => String(row.month)}
              />
            ) : null}
          </div>
        </Card>
      </div>
    </div>
  );
}
