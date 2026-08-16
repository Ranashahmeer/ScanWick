/**
 * Ingestion panels — prototype screens 06, 07, 08, 09, 12 and 72.
 *
 * Two rules shape this group. A rejection is recoverable and a confident
 * wrong answer is not, so screen 12 reads as care rather than failure —
 * calm, specific, never apologetic, never a stack trace. And processing
 * never shows a bare spinner: every stage writes a status, so a user always
 * knows which statement is at which step.
 */

import { Btn, Card, Hint, Pill, Row, Src, Tbl } from "@/components/sw";
import type { BankSource } from "../sources";

/* ---------------------------------------------------- screen 72 */

/** Per-source instructions. The single biggest drop-off point in the product. */
export function SourceGuide({ source }: { source: BankSource }) {
  return (
    <div>
      <Card title="How to get your statement" sub={`${source.label} · ${source.formats}`} style={{ marginBottom: 14 }}>
        <ol style={{ marginLeft: 16, fontSize: 12.5, lineHeight: 1.85, color: "var(--ink2)" }}>
          {source.steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>

        {source.passwordHint ? (
          <div
            style={{
              marginTop: 10,
              padding: 10,
              background: "var(--warnbg)",
              borderRadius: 8,
              fontSize: 11.5,
              color: "#5C4A16",
            }}
          >
            <b>Password:</b> {source.passwordHint}
          </div>
        ) : null}

        {source.note ? (
          <div
            style={{
              marginTop: 10,
              padding: 10,
              background: source.noteTone === "warn" ? "var(--warnbg)" : "var(--g50)",
              borderRadius: 8,
              fontSize: 11.5,
              color: source.noteTone === "warn" ? "#5C4A16" : "var(--ink2)",
            }}
          >
            {source.note}
          </div>
        ) : null}

        <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          {source.parser === "dedicated" ? (
            <>
              <Pill tone="a">Parser ready</Pill>
              <span style={{ fontSize: 11.5, color: "var(--ink3)" }}>Dedicated {source.label} reader</span>
            </>
          ) : (
            <>
              <Pill tone="c">Limited</Pill>
              <span style={{ fontSize: 11.5, color: "var(--ink3)" }}>
                Careful generic reader until a dedicated parser ships
              </span>
            </>
          )}
        </div>
      </Card>


    </div>
  );
}

/* ---------------------------------------------------- screen 06 */

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
    <Row cols="21">
      <Card title="Wallets" sub={`${wallets.length} sources`}>
        <Row cols={4} style={{ gap: 10 }}>
          {wallets.map((source) => (
            <SourceTile
              key={source.id}
              source={source}
              onUpload={() => onUpload(source.id)}
              onConnect={() => onConnect(source.id)}
            />
          ))}
        </Row>

        <h3 style={{ marginTop: 20 }}>Banks</h3>
        <div className="sub">{banks.length} sources</div>
        <Row cols={3} style={{ gap: 10 }}>
          {banks.map((source) => (
            <SourceTile
              key={source.id}
              source={source}
              onUpload={() => onUpload(source.id)}
              onConnect={() => onConnect(source.id)}
            />
          ))}
        </Row>

        <Hint style={{ marginTop: 14 }}>
          Connecting gives Tier A — the highest confidence, no file passes through your hands, and it is the only way to
          keep a lender updated after a loan. Uploading gives Tier B.
        </Hint>
      </Card>


    </Row>
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
    <div
      className="ph pick"
      style={{ height: 78, flexDirection: "column", gap: 4 }}
      onClick={onUpload}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onUpload();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`Add ${source.label}`}
    >
      <b style={{ color: "var(--ink)" }}>{source.label}</b>
      <button
        type="button"
        className="pill a"
        style={{ border: 0, cursor: "pointer", font: "inherit", fontSize: 10.5, fontWeight: 700 }}
        onClick={(e) => {
          e.stopPropagation();
          onConnect();
        }}
      >
        Connect
      </button>
      <span style={{ fontSize: 9.5 }}>or upload</span>
    </div>
  );
}

/* ---------------------------------------------------- screen 07 */

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
    <>
      <div
        style={{
          marginTop: 14,
          padding: 12,
          border: "1px solid var(--line)",
          borderRadius: 8,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div>
          <b style={{ fontSize: 12.5 }}>{fileName}</b>
          <Hint>{fileSizeLabel}</Hint>
        </div>
        <Pill tone="a">Ready</Pill>
      </div>
      <div style={{ marginTop: 14, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Btn onClick={onAnalyse} disabled={analysing}>
          {analysing ? "Starting…" : "Analyse this statement"}
        </Btn>
        <Btn tone="gho" onClick={onClear} disabled={analysing}>
          Choose another file
        </Btn>
      </div>
    </>
  );
}

/* ---------------------------------------------------- screen 08 */

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
    <Row cols={2}>
      <Card
        title="This statement is password-protected"
        sub={`Enter the password your bank uses for ${fileName}. We use it to open the file and never store it.`}
        style={{ maxWidth: 440 }}
      >
        <div className="field">
          <label htmlFor="stmt-password">Statement password</label>
          <input
            id="stmt-password"
            type="password"
            className={`inp${error ? " err" : ""}`}
            value={password}
            onChange={(event) => onPasswordChange(event.target.value)}
            autoComplete="off"
            autoFocus
            onKeyDown={(event) => {
              if (event.key === "Enter" && password && !submitting) onSubmit();
            }}
          />
          {source.passwordHint ? <Hint>{source.passwordHint}</Hint> : null}
        </div>

        {error ? (
          <div
            style={{
              padding: "10px 12px",
              background: "var(--warnbg)",
              border: "1px solid #E4C77E",
              borderRadius: 8,
              fontSize: 12.5,
              color: "#5C4A16",
              marginBottom: 12,
            }}
            role="alert"
          >
            {error}
            <div style={{ marginTop: 4 }}>
              The file was not rejected — only the password did not open it. Try again.
            </div>
          </div>
        ) : null}

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn onClick={onSubmit} disabled={submitting || !password}>
            {submitting ? "Unlocking…" : "Unlock and analyse"}
          </Btn>
          <Btn tone="gho" onClick={onCancel} disabled={submitting}>
            Cancel
          </Btn>
        </div>

        <div
          style={{
            marginTop: 16,
            padding: 11,
            background: "var(--g50)",
            borderRadius: 8,
            fontSize: 11.5,
            color: "var(--ink2)",
          }}
        >
          🔒 The password is used once, in memory, to open this file. It is never written to disk, never logged and never
          stored against your account.
        </div>
      </Card>


    </Row>
  );
}

/* ---------------------------------------------------- screen 09 */

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
  const percent = Math.min(95, (stageIndex + 1) * 22);
  const mark = sourceLabel.slice(0, 2).toUpperCase();

  return (
    <Row cols={2}>
      <Card
        title="Reading your statement"
        sub={`${sourceLabel} · ${fileName}. This usually takes under a minute — you can leave this page.`}
      >
        <Tbl>
          <table>
            <tbody>
              {stages.map((label, index) => {
                const state = index < stageIndex ? "done" : index === stageIndex ? "running" : "waiting";
                return (
                  <tr key={label}>
                    <td>
                      <Src mark={mark}>{sourceLabel}</Src>
                    </td>
                    <td>{label}</td>
                    <td
                      className="num"
                      style={{
                        color:
                          state === "done" ? "var(--g600)" : state === "running" ? "var(--warn)" : "var(--ink3)",
                      }}
                    >
                      {state === "done" ? "✓ done" : state}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Tbl>

        <div
          className="bar"
          style={{ marginTop: 16 }}
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
        >
          <i style={{ width: `${percent}%` }} />
        </div>
        <Hint style={{ marginTop: 7 }}>
          {stageIndex >= stages.length - 1
            ? "This is taking longer than usual. You can leave this page — we will email you when it is ready."
            : ""}
        </Hint>
      </Card>


    </Row>
  );
}

/* ---------------------------------------------------- screen 12 */

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
    <Row cols={2}>
      <Card title="We could not read this statement" sub="Nothing has been analysed from this file.">
        <div
          style={{
            padding: 14,
            border: "1px solid var(--line)",
            borderLeft: "4px solid var(--warn)",
            borderRadius: 8,
            background: "var(--warnbg)",
            marginBottom: 14,
          }}
        >
          <b style={{ fontSize: 12.5, color: "var(--warn)" }}>{title}</b>
          <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 6 }}>{detail}</div>
        </div>

        <b style={{ fontSize: 12.5 }}>What you can do</b>
        <ul style={{ margin: "8px 0 0 17px", fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.9 }}>
          <li>Re-download the statement directly from your bank app rather than forwarding an email copy</li>
          <li>Choose PDF rather than a screenshot or scan</li>
          <li>Tell us which bank issued it and we will add support</li>
        </ul>

        <div style={{ marginTop: 14, display: "flex", gap: 8, flexWrap: "wrap" }}>
          {actions.map((action) => (
            <Btn key={action.label} sm tone={action.primary === false ? "gho" : "primary"} onClick={action.onClick}>
              {action.label}
            </Btn>
          ))}
        </div>
      </Card>


    </Row>
  );
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B · selected just now`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB · selected just now`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB · selected just now`;
}
