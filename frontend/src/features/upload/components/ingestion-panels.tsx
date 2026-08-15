import type { BankSource } from "../sources";

export function SourceGuide({ source }: { source: BankSource }) {
  return (
    <aside className="ing-source-guide">
      <h3>How to get your statement</h3>
      <p className="ing-source-guide-sub">Per-source instructions for {source.label}</p>
      <ol>
        {source.steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      {source.passwordHint ? (
        <div className="ing-note ing-note-warn">
          <strong>Password:</strong> {source.passwordHint}
        </div>
      ) : null}
      {source.note ? (
        <div className={`ing-note ${source.noteTone === "warn" ? "ing-note-warn" : "ing-note-info"}`}>
          {source.note}
        </div>
      ) : null}
      {source.parser === "dedicated" ? (
        <p className="ing-source-guide-meta">
          <span className="ing-pill ing-pill-a">Parser ready</span>
          Dedicated {source.label} reader
        </p>
      ) : (
        <p className="ing-source-guide-meta">
          <span className="ing-pill ing-pill-c">Limited</span>
          Generic reader until a dedicated parser ships
        </p>
      )}
    </aside>
  );
}

/** Prototype s06 — Add accounts hub. Tiles open Connect or Upload. */
export function SourceHub({
  sources,
  onUpload,
  onConnect,
}: {
  sources: BankSource[];
  onUpload: (sourceId: string) => void;
  onConnect: (sourceId: string) => void;
}) {
  const wallets = sources.filter((s) => s.group === "wallet");
  const banks = sources.filter((s) => s.group === "bank");

  return (
    <div className="ing-hub">
      <div className="ing-hub-main">
        <div className="ing-source-group">
          <div className="ing-source-group-head">
            <h3>Wallets</h3>
            <span>{wallets.length} sources</span>
          </div>
          <div className="ing-source-grid">
            {wallets.map((source) => (
              <SourceTile
                key={source.id}
                source={source}
                onUpload={() => onUpload(source.id)}
                onConnect={() => onConnect(source.id)}
              />
            ))}
          </div>
        </div>

        <div className="ing-source-group">
          <div className="ing-source-group-head">
            <h3>Banks</h3>
            <span>{banks.length} sources</span>
          </div>
          <div className="ing-source-grid ing-source-grid-banks">
            {banks.map((source) => (
              <SourceTile
                key={source.id}
                source={source}
                onUpload={() => onUpload(source.id)}
                onConnect={() => onConnect(source.id)}
              />
            ))}
          </div>
        </div>

        <p className="ing-source-foot">
          Connecting gives Tier A — highest confidence, no file through your hands.
          Uploading a statement gives Tier B.
        </p>
      </div>

      <aside className="ing-hub-side">
        <div className="ing-hub-note">
          <strong>All thirteen sources</strong>
          <p>
            Every source listed has been reverse-engineered from a real statement.
            Nine have dedicated parsers ready; four use a careful generic reader
            until theirs ship. Treat them as equal in the interface.
          </p>
        </div>
      </aside>
    </div>
  );
}

function SourceTile({
  source,
  onUpload,
  onConnect,
}: {
  source: BankSource;
  onUpload: () => void;
  onConnect: () => void;
}) {
  return (
    <div className="ing-source-tile">
      <button
        type="button"
        className="ing-source-tile-main"
        onClick={onUpload}
        aria-label={`Upload ${source.label} statement`}
      >
        <span className="ing-source-mark" aria-hidden>
          {source.short}
        </span>
        <strong>{source.label}</strong>
      </button>
      <div className="ing-source-tile-actions">
        <button
          type="button"
          className="ing-pill ing-pill-a ing-tile-action"
          onClick={onConnect}
          aria-label={`Connect ${source.label}`}
        >
          Connect
        </button>
        <button type="button" className="ing-tile-upload" onClick={onUpload}>
          or upload
        </button>
      </div>
    </div>
  );
}

/** Prototype s07 — file chosen, waiting for Analyse. */
export function FileReadyCard({
  fileName,
  fileSizeLabel,
  onAnalyse,
  onClear,
  analysing,
}: {
  fileName: string;
  fileSizeLabel: string;
  onAnalyse: () => void;
  onClear: () => void;
  analysing: boolean;
}) {
  return (
    <div className="ing-file-ready">
      <div className="ing-file-ready-row">
        <div>
          <strong>{fileName}</strong>
          <div className="ing-hint">{fileSizeLabel}</div>
        </div>
        <span className="ing-pill ing-pill-a">Ready</span>
      </div>
      <div className="ing-password-actions">
        <button type="button" className="ing-btn" onClick={onAnalyse} disabled={analysing}>
          {analysing ? "Starting…" : "Analyse this statement"}
        </button>
        <button type="button" className="ing-btn ing-btn-ghost" onClick={onClear} disabled={analysing}>
          Choose another file
        </button>
      </div>
    </div>
  );
}

export function PasswordUnlockPanel({
  source,
  fileName,
  password,
  error,
  submitting,
  onPasswordChange,
  onSubmit,
  onCancel,
}: {
  source: BankSource;
  fileName: string;
  password: string;
  error: string | null;
  submitting: boolean;
  onPasswordChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="ing-password-panel">
      <h3>This statement is password-protected</h3>
      <p>
        Enter the password your bank uses for <strong>{fileName}</strong>. We use
        it once in memory to open the file and never store it.
      </p>

      <label className="ing-field">
        <span>Statement password</span>
        <input
          type="password"
          className="ing-input"
          value={password}
          onChange={(event) => onPasswordChange(event.target.value)}
          autoComplete="off"
          autoFocus
          onKeyDown={(event) => {
            if (event.key === "Enter" && password && !submitting) onSubmit();
          }}
        />
        {source.passwordHint ? <span className="ing-hint">{source.passwordHint}</span> : null}
      </label>

      {error ? <div className="ing-note ing-note-warn">{error}</div> : null}

      <div className="ing-password-actions">
        <button type="button" className="ing-btn" onClick={onSubmit} disabled={submitting || !password}>
          {submitting ? "Unlocking…" : "Unlock and analyse"}
        </button>
        <button type="button" className="ing-btn ing-btn-ghost" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>

      <div className="ing-note ing-note-info">
        The password is used once, in memory, to open this file. It is never
        written to disk, never logged, and never stored against your account.
      </div>
    </div>
  );
}

export function ProcessingStages({
  fileName,
  sourceLabel,
  stageIndex,
}: {
  fileName: string;
  sourceLabel: string;
  stageIndex: number;
}) {
  const stages = [
    "Identifying source",
    "Extracting transactions",
    "Checking the statement",
    "Writing quality report",
  ];

  return (
    <div className="ing-processing">
      <h3>Reading your statement</h3>
      <p>
        {sourceLabel} · {fileName}. This usually takes under a minute.
      </p>
      <table className="ing-stage-table">
        <tbody>
          {stages.map((label, index) => {
            const state =
              index < stageIndex ? "done" : index === stageIndex ? "running" : "waiting";
            return (
              <tr key={label}>
                <td>
                  <span className="ing-src-chip">
                    <b>{sourceLabel.slice(0, 2).toUpperCase()}</b>
                    {sourceLabel}
                  </span>
                </td>
                <td>{label}</td>
                <td className={`ing-stage-${state}`}>
                  {state === "done" ? "done" : state === "running" ? "running" : "waiting"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div
        className="ing-progress-track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.min(95, (stageIndex + 1) * 22)}
      >
        <i style={{ width: `${Math.min(95, (stageIndex + 1) * 22)}%` }} />
      </div>
      <p className="ing-hint">Every stage writes a status — you will not be left on a blank spinner.</p>
    </div>
  );
}

export function RejectedPanel({
  title,
  detail,
  actions,
}: {
  title: string;
  detail: string;
  actions: { label: string; onClick: () => void; primary?: boolean }[];
}) {
  return (
    <div className="ing-rejected">
      <h3>{title}</h3>
      <p className="ing-rejected-sub">Nothing has been analysed from this file.</p>
      <div className="ing-rejected-callout">
        <strong>{title}</strong>
        <p>{detail}</p>
      </div>
      <strong className="ing-rejected-next">What you can do</strong>
      <div className="ing-password-actions">
        {actions.map((action) => (
          <button
            key={action.label}
            type="button"
            className={`ing-btn ${action.primary === false ? "ing-btn-ghost" : ""}`}
            onClick={action.onClick}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B · selected just now`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB · selected just now`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB · selected just now`;
}
