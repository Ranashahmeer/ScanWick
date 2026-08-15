import { useState } from "react";
import { Clock3, Plus, Trash2 } from "lucide-react";
import { Badge, PageHead, Table } from "@/features/intelligence/components/shared";
import { Toggle } from "@/features/account/components/toggle";

interface ScheduledReport {
  id: string;
  report: string;
  frequency: string;
  nextRun: string;
  recipients: string;
  format: "PDF" | "Excel";
  on: boolean;
}

const initialSchedules: ScheduledReport[] = [
  {
    id: "sch-1",
    report: "Executive Overview",
    frequency: "Weekly · Mon 07:00",
    nextRun: "23 Jun",
    recipients: "owner@lumio.ng +2",
    format: "PDF",
    on: true,
  },
  {
    id: "sch-2",
    report: "Inventory Health",
    frequency: "Daily · 06:00",
    nextRun: "tomorrow",
    recipients: "tunde@lumio.ng",
    format: "Excel",
    on: true,
  },
  {
    id: "sch-3",
    report: "Quarter Post-Mortem",
    frequency: "Quarterly",
    nextRun: "1 Jul",
    recipients: "owner@lumio.ng",
    format: "PDF",
    on: false,
  },
];

export function ScheduledReportsPage() {
  const [schedules, setSchedules] = useState<ScheduledReport[]>(initialSchedules);
  const [showForm, setShowForm] = useState(false);
  const [reportName, setReportName] = useState("");
  const [frequency, setFrequency] = useState("Weekly · Mon 07:00");
  const [recipients, setRecipients] = useState("");
  const [format, setFormat] = useState<"PDF" | "Excel">("PDF");

  const addSchedule = () => {
    if (!reportName.trim() || !recipients.trim()) return;
    setSchedules((current) => [
      { id: `sch-${Date.now()}`, report: reportName.trim(), frequency, nextRun: "pending", recipients: recipients.trim(), format, on: true },
      ...current,
    ]);
    setReportName("");
    setRecipients("");
    setShowForm(false);
  };

  return (
    <div>
      <div className="rpt-page-head-row">
        <PageHead
          module="Reports"
          breadcrumb="Scheduled Reports"
          title="Scheduled Reports"
          description="Automatically generated and emailed on your cadence."
        />
        <div className="rpt-actions-row">
          <button type="button" className="rpt-btn rpt-btn-primary" onClick={() => setShowForm((open) => !open)}>
            <Plus size={14} strokeWidth={2.6} /> New schedule
          </button>
        </div>
      </div>

      {showForm ? (
        <div className="fi-card fi-row-tight">
          <div className="acct-form-grid">
            <label className="acct-field">
              <span>Report name</span>
              <input type="text" value={reportName} onChange={(event) => setReportName(event.target.value)} placeholder="e.g. Executive Overview" />
            </label>
            <label className="acct-field">
              <span>Frequency</span>
              <select value={frequency} onChange={(event) => setFrequency(event.target.value)}>
                <option>Daily · 06:00</option>
                <option>Weekly · Mon 07:00</option>
                <option>Monthly · 1st 07:00</option>
                <option>Quarterly</option>
              </select>
            </label>
            <label className="acct-field">
              <span>Recipients</span>
              <input type="text" value={recipients} onChange={(event) => setRecipients(event.target.value)} placeholder="owner@lumio.ng" />
            </label>
            <label className="acct-field">
              <span>Format</span>
              <select value={format} onChange={(event) => setFormat(event.target.value as "PDF" | "Excel")}>
                <option value="PDF">PDF</option>
                <option value="Excel">Excel</option>
              </select>
            </label>
          </div>
          <div className="rpt-form-actions">
            <button type="button" className="rpt-btn rpt-btn-outline" onClick={() => setShowForm(false)}>
              Cancel
            </button>
            <button type="button" className="rpt-btn rpt-btn-primary" onClick={addSchedule}>
              Create schedule
            </button>
          </div>
        </div>
      ) : null}

      {schedules.length === 0 ? (
        <div className="fi-empty fi-row-tight">
          <span className="fi-empty-icon">
            <Clock3 size={18} strokeWidth={2.2} />
          </span>
          <h3>No scheduled reports</h3>
          <p>Schedule a report to have it generated and emailed automatically.</p>
          <button type="button" className="rpt-btn rpt-btn-primary" onClick={() => setShowForm(true)}>
            <Plus size={14} strokeWidth={2.6} /> New schedule
          </button>
        </div>
      ) : (
        <div className="fi-row-tight">
          <Table
            columns={[
              { key: "report", label: "Report" },
              { key: "frequency", label: "Frequency" },
              { key: "nextRun", label: "Next run" },
              { key: "recipients", label: "Recipients" },
              { key: "format", label: "Format" },
              { key: "on", label: "On", align: "right" },
              { key: "actions", label: "", align: "right" },
            ]}
            rows={schedules.map((schedule) => ({
              report: schedule.report,
              frequency: schedule.frequency,
              nextRun: schedule.nextRun,
              recipients: schedule.recipients,
              format: <Badge tone={schedule.format === "PDF" ? "danger" : "success"}>{schedule.format}</Badge>,
              on: (
                <Toggle
                  checked={schedule.on}
                  label={`Toggle ${schedule.report}`}
                  onChange={(checked) =>
                    setSchedules((current) => current.map((item) => (item.id === schedule.id ? { ...item, on: checked } : item)))
                  }
                />
              ),
              actions: (
                <button
                  type="button"
                  className="rpt-btn rpt-btn-danger rpt-btn-sm"
                  onClick={() => setSchedules((current) => current.filter((item) => item.id !== schedule.id))}
                >
                  <Trash2 size={12} strokeWidth={2.6} /> Delete
                </button>
              ),
            }))}
            rowKey={(_row, index) => schedules[index]?.id ?? String(index)}
          />
        </div>
      )}
    </div>
  );
}
