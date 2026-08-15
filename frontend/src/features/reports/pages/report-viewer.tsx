import { useEffect, useRef, useState } from "react";
import { Download, Loader2, Printer, Share2 } from "lucide-react";
import { Bar, BarChart, Cell, ResponsiveContainer, XAxis } from "recharts";
import { Badge, Card } from "@/features/intelligence/components/shared";
import type { GeneratedReport } from "../mock-data";

export function ReportViewerPage({ report, onBack }: { report: GeneratedReport; onBack: () => void }) {
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(
    () => () => {
      if (timerRef.current) clearInterval(timerRef.current);
    },
    [],
  );

  const handleDownloadPdf = () => {
    if (generating) return;
    setGenerating(true);
    setProgress(10);
    timerRef.current = setInterval(() => {
      setProgress((current) => {
        const next = current + 15;
        if (next >= 100) {
          if (timerRef.current) clearInterval(timerRef.current);
          setTimeout(() => setGenerating(false), 500);
          return 100;
        }
        return next;
      });
    }, 220);
  };

  return (
    <div>
      <div className="rpt-page-head-row">
        <div className="fi-page-head">
          <p className="fi-breadcrumb">
            <button type="button" className="rpt-link" onClick={onBack}>
              Reports
            </button>{" "}
            <strong>Report Viewer</strong>
          </p>
          <h1>{report.title}</h1>
          <p>
            Period {report.period} · generated {report.generatedAt} · source: {report.source}
          </p>
        </div>
        <div className="rpt-actions-row">
          <button type="button" className="rpt-btn rpt-btn-primary" onClick={handleDownloadPdf} disabled={generating}>
            <Download size={13} strokeWidth={2.6} /> PDF
          </button>
          <button type="button" className="rpt-btn rpt-btn-outline">
            <Download size={13} strokeWidth={2.6} /> Excel
          </button>
          <button type="button" className="rpt-btn rpt-btn-outline">
            <Share2 size={13} strokeWidth={2.6} /> Share
          </button>
          <button type="button" className="rpt-btn rpt-btn-outline">
            <Printer size={13} strokeWidth={2.6} /> Print
          </button>
        </div>
      </div>

      {generating ? (
        <div className="dqr-banner fi-row-tight">
          <Loader2 size={16} strokeWidth={2.4} className="rpt-spin" />
          <p>Generating PDF… progress {progress}%</p>
        </div>
      ) : null}

      <div className="fi-grid-3">
        <div className="fi-card fi-stat-tile">
          <span className="fi-stat-label">Forecast vs actual</span>
          <span className="fi-stat-value">{report.stats.forecastVsActual}</span>
          <span
            className={`fi-stat-delta ${report.stats.forecastVsActualDelta.startsWith("-") ? "fi-stat-delta-down" : "fi-stat-delta-up"}`}
          >
            {report.stats.forecastVsActualDelta}
          </span>
        </div>
        <div className="fi-card fi-stat-tile">
          <span className="fi-stat-label">Total slippage</span>
          <span className="fi-stat-value">{report.stats.totalSlippage}</span>
        </div>
        <div className="fi-card fi-stat-tile">
          <span className="fi-stat-label">Forecast confidence</span>
          <span className="fi-stat-value">{report.stats.confidence}</span>
          <Badge tone={report.stats.confidence === "High" ? "success" : report.stats.confidence === "Medium" ? "warning" : "danger"}>
            shown on export
          </Badge>
        </div>
      </div>

      <Card className="fi-row-tight">
        <ResponsiveContainer width="100%" height={190}>
          <BarChart data={report.chart}>
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: "rgba(180,200,190,.6)" }} axisLine={false} tickLine={false} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={64}>
              {report.chart.map((point, index) => (
                <Cell key={point.label} fill={index === 0 ? "rgba(127,199,163,.42)" : "#7fc7a3"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <p className="rpt-note">{report.note}</p>
    </div>
  );
}
