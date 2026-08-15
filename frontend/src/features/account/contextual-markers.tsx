import { Info } from "lucide-react";
import { useState } from "react";

interface Marker {
  id: string;
  label: string;
  range: string;
}

const initialMarkers: Marker[] = [
  { id: "promo", label: "Promotion Period", range: "15–28 Mar 2026" },
  { id: "loan", label: "Loan Disbursement Period", range: "2–3 May 2026" },
  { id: "outage", label: "Platform Outage", range: "18 May 2026" },
];

const labelOptions = ["Promotion Period", "Loan Disbursement Period", "Platform Outage", "Custom"];

function formatRange(startDate: string, endDate: string) {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const startText = start.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  const endText = end.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  return startDate === endDate ? endText : `${startText} – ${endText}`;
}

export function ContextualMarkers() {
  const [markers, setMarkers] = useState(initialMarkers);
  const [startDate, setStartDate] = useState("2026-03-15");
  const [endDate, setEndDate] = useState("2026-03-26");
  const [label, setLabel] = useState("Promotion Period");
  const [customLabel, setCustomLabel] = useState("");

  const addMarker = () => {
    const finalLabel = label === "Custom" ? customLabel.trim() : label;
    if (!finalLabel) return;

    setMarkers((current) => [
      ...current,
      { id: `${finalLabel}-${Date.now()}`, label: finalLabel, range: formatRange(startDate, endDate) },
    ]);
    setCustomLabel("");
  };

  const deleteMarker = (id: string) => {
    setMarkers((current) => current.filter((marker) => marker.id !== id));
  };

  const previewLabel = label === "Custom" ? customLabel || "Custom" : label;

  return (
    <div className="acct-stack">
      <div className="acct-callout">
        <Info size={15} strokeWidth={2.2} />
        <p>
          Tagged periods are flagged <code>is_anomalous</code> and excluded from model training
          across all three modules — they won't distort the Holt-Winters inventory forecast, the
          RFM/Kaplan-Meier churn models, or the sales forecast confidence score.
        </p>
      </div>

      <div className="acct-card">
        <h2>Create a marker</h2>

        <div className="acct-form-grid">
          <label className="acct-field">
            <span>Start date</span>
            <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
          </label>
          <label className="acct-field">
            <span>End date</span>
            <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
          </label>
          <label className="acct-field">
            <span>Label</span>
            <select value={label} onChange={(event) => setLabel(event.target.value)}>
              {labelOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="acct-field">
            <span>Custom label (if "Custom")</span>
            <input
              type="text"
              placeholder="e.g. Generator fuel crisis"
              value={customLabel}
              disabled={label !== "Custom"}
              onChange={(event) => setCustomLabel(event.target.value)}
            />
          </label>
        </div>

        <div className="acct-marker-preview">
          <svg viewBox="0 0 400 90" preserveAspectRatio="none" className="acct-marker-chart">
            <rect x="150" y="0" width="100" height="90" className="acct-marker-band" />
            <polyline
              points="0,60 40,55 80,62 120,50 150,58 190,30 220,26 250,40 300,40 340,45 400,25"
              fill="none"
              stroke="#7fc7a3"
              strokeWidth="2"
            />
          </svg>
          <span className="acct-marker-tag">{previewLabel}</span>
        </div>
        <p className="acct-card-hint">Markers render on every chart as a shaded vertical band with a label tag.</p>

        <button type="button" className="dqr-action-primary acct-mt" onClick={addMarker}>
          Add marker
        </button>
      </div>

      <div className="acct-card">
        <h2>Active markers</h2>
        <div className="acct-marker-list">
          {markers.map((marker) => (
            <div className="acct-marker-row" key={marker.id}>
              <span className="acct-marker-dot" />
              <div className="acct-marker-row-body">
                <strong>{marker.label}</strong>
                <span>{marker.range}</span>
              </div>
              <button type="button" className="acct-btn-outline" onClick={() => deleteMarker(marker.id)}>
                Delete
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
