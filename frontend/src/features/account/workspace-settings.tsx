import { useState } from "react";
import { Segmented } from "./components/segmented";
import { Toggle } from "./components/toggle";

type AdKillMode = "manual" | "auto";
type AttributionModel = "first" | "last" | "blended";
type DataRefresh = "manual" | "daily" | "hourly";

export function WorkspaceSettings() {
  const [adKillMode, setAdKillMode] = useState<AdKillMode>("manual");
  const [attribution, setAttribution] = useState<AttributionModel>("first");
  const [dataRefresh, setDataRefresh] = useState<DataRefresh>("daily");
  const [emailChannel, setEmailChannel] = useState(true);
  const [inAppChannel, setInAppChannel] = useState(true);
  const [slackChannel, setSlackChannel] = useState(false);

  return (
    <div className="acct-stack">
      <div className="acct-card">
        <h2>Currency</h2>
        <p className="acct-card-hint">
          All values normalise to your base currency; originals are always shown alongside
          conversions.
        </p>
        <div className="acct-setting-row">
          <div>
            <strong>Base currency</strong>
            <p>Reporting currency across all modules</p>
          </div>
          <select className="acct-inline-select" defaultValue="NGN">
            <option value="NGN">NGN — Nigerian Naira ₦</option>
            <option value="USD">USD — US Dollar $</option>
            <option value="GHS">GHS — Ghanaian Cedi ₵</option>
          </select>
        </div>
        <div className="acct-setting-row">
          <div>
            <strong>Exchange-rate source</strong>
            <p>Rate applied at each transaction's date</p>
          </div>
          <select className="acct-inline-select" defaultValue="cbn">
            <option value="cbn">CBN official rate</option>
            <option value="parallel">Parallel market rate</option>
          </select>
        </div>
      </div>

      <div className="acct-card">
        <h2>Commerce</h2>
        <p className="acct-card-hint">Affects Net Margin, Profit Leak, Unit Margin, and the Ad-Kill Switch.</p>

        <div className="acct-setting-row">
          <div>
            <strong>Return cost — global default</strong>
            <p>Average cost to process one return (label + repackaging). SKU-level overrides available.</p>
          </div>
          <div className="acct-setting-controls">
            <input type="text" className="acct-inline-input" defaultValue="₦1,200" />
            <button type="button" className="acct-btn-outline">
              SKU overrides
            </button>
          </div>
        </div>

        <div className="acct-setting-row">
          <div>
            <strong>Ad-Kill Switch mode</strong>
            <p>Manual Approval is the default and recommended starting mode.</p>
          </div>
          <Segmented
            options={[
              { id: "manual", label: "Manual" },
              { id: "auto", label: "Auto-Pause" },
            ]}
            value={adKillMode}
            onChange={setAdKillMode}
          />
        </div>

        <div className="acct-setting-row">
          <div>
            <strong>Inventory cover threshold</strong>
            <p>Trigger when days of cover falls below</p>
          </div>
          <input type="text" className="acct-inline-input acct-inline-input-sm" defaultValue="7 days" />
        </div>

        <div className="acct-setting-row">
          <div>
            <strong>Attribution model</strong>
            <p>Switching recalculates all channel metrics simultaneously.</p>
          </div>
          <Segmented
            options={[
              { id: "first", label: "First-Click" },
              { id: "last", label: "Last-Click" },
              { id: "blended", label: "Blended" },
            ]}
            value={attribution}
            onChange={setAttribution}
          />
        </div>
      </div>

      <div className="acct-card">
        <h2>Notifications &amp; data</h2>
        <div className="acct-setting-row">
          <div>
            <strong>Notification channels</strong>
            <p>Email · In-app · Slack</p>
          </div>
          <div className="acct-channel-toggles">
            <label>
              <Toggle checked={emailChannel} onChange={setEmailChannel} label="Email" />
              Email
            </label>
            <label>
              <Toggle checked={inAppChannel} onChange={setInAppChannel} label="In-app" />
              In-app
            </label>
            <label>
              <Toggle checked={slackChannel} onChange={setSlackChannel} label="Slack" />
              Slack
            </label>
          </div>
        </div>
        <div className="acct-setting-row">
          <div>
            <strong>Data refresh</strong>
            <p>Manual (Free) · Daily (Basic) · Every few hours (Premium)</p>
          </div>
          <Segmented
            options={[
              { id: "manual", label: "Manual" },
              { id: "daily", label: "Daily" },
              { id: "hourly", label: "Hourly" },
            ]}
            value={dataRefresh}
            onChange={setDataRefresh}
          />
        </div>
      </div>
    </div>
  );
}
