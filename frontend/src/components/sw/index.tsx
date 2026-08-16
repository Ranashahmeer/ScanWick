/**
 * Scanwick prototype primitives.
 *
 * One component per primitive in the prototype's design system (screen 00),
 * so every converted screen composes the same pieces instead of restating
 * the markup. Each renders the prototype's own class names, which the
 * `.sw`-scoped stylesheet in src/styles/scanwick.css supplies.
 *
 * Three of these carry product rules rather than styling preferences and
 * must not be worked around:
 *   - <Na>       an unavailable value renders as the amber chip with its
 *                reason. Never a zero, never a dash, never a blank cell.
 *   - <Pill>     tier and status vocabulary; audit findings use the neutral
 *                `n` tone, never `d`.
 *   - <Coverage> coverage is always on screen, never behind a tooltip.
 */

import type {
  AnchorHTMLAttributes,
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { useEffect, useId } from "react";
import { money } from "./format";

const cx = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(" ");

/* ---------------------------------------------------------------- layout */

export function Row({
  cols,
  children,
  className,
  style,
}: {
  cols: 2 | 3 | 4 | "21" | "12";
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div className={cx("row", `r${cols}`, className)} style={style}>
      {children}
    </div>
  );
}

export function Card({
  title,
  sub,
  children,
  className,
  style,
  action,
}: {
  title?: ReactNode;
  sub?: ReactNode;
  children?: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  /** Rendered on the same line as the title, right-aligned. */
  action?: ReactNode;
}) {
  const hasHead = title != null || sub != null;
  return (
    <div className={cx("card", className)} style={style}>
      {hasHead ? (
        action ? (
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 14,
              marginBottom: 14,
              flexWrap: "wrap",
            }}
          >
            <div>
              {title != null ? <h3>{title}</h3> : null}
              {sub != null ? (
                <div className="sub" style={{ marginBottom: 0 }}>
                  {sub}
                </div>
              ) : null}
            </div>
            {action}
          </div>
        ) : (
          <>
            {title != null ? <h3>{title}</h3> : null}
            {sub != null ? <div className="sub">{sub}</div> : null}
          </>
        )
      ) : null}
      {children}
    </div>
  );
}

export function ScreenHead({
  title,
  meta,
  tag,
  tagTone = "default",
  action,
}: {
  title: ReactNode;
  meta?: ReactNode;
  tag?: ReactNode;
  tagTone?: "default" | "s2" | "s3" | "sys" | "pub";
  action?: ReactNode;
}) {
  return (
    <div className="scrhead">
      <div>
        <h1>{title}</h1>
        {meta ? <div className="meta">{meta}</div> : null}
      </div>
      {action ?? (tag ? <span className={cx("tag", tagTone !== "default" && tagTone)}>{tag}</span> : null)}
    </div>
  );
}

/* --------------------------------------------------------------- buttons */

type BtnTone = "primary" | "sec" | "gho" | "dgr";

export function Btn({
  tone = "primary",
  sm,
  block,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: BtnTone; sm?: boolean; block?: boolean }) {
  return (
    <button
      type="button"
      className={cx("btn", tone !== "primary" && tone, sm && "sm", block && "blk", className)}
      {...rest}
    >
      {children}
    </button>
  );
}

export function BtnLink({
  tone = "primary",
  sm,
  block,
  className,
  children,
  ...rest
}: AnchorHTMLAttributes<HTMLAnchorElement> & { tone?: BtnTone; sm?: boolean; block?: boolean }) {
  return (
    <a className={cx("btn", tone !== "primary" && tone, sm && "sm", block && "blk", className)} {...rest}>
      {children}
    </a>
  );
}

/* ---------------------------------------------------------- status atoms */

export type PillTone = "a" | "b" | "c" | "d" | "n";

export function Pill({ tone = "n", children }: { tone?: PillTone; children: ReactNode }) {
  return <span className={cx("pill", tone)}>{children}</span>;
}

/** Source confidence tier. A=direct API, B=verified file, C=unverified, D=rejected. */
export function Tier({ tier, long = false }: { tier: "A" | "B" | "C" | "D"; long?: boolean }) {
  const tone: PillTone = tier === "A" ? "a" : tier === "B" ? "b" : tier === "C" ? "c" : "d";
  const label = { A: "Direct", B: "Verified file", C: "Unverified", D: "Rejected" }[tier];
  return <Pill tone={tone}>{long ? `Tier ${tier} · ${label}` : tier}</Pill>;
}

/**
 * The unavailable state. Renders the amber chip and carries the reason.
 * Passing no reason is allowed only where the surrounding copy already
 * states it (the prototype's own "n/a" cells on screens 17 and 18).
 */
export function Na({ reason, label = "Unavailable" }: { reason?: string; label?: string }) {
  return (
    <span className="na" title={reason}>
      {label}
    </span>
  );
}

export type Severity = "i" | "w" | "a" | "u";

export function Sev({ level }: { level: Severity }) {
  const name = { i: "Informational", w: "Watch", a: "Act", u: "Urgent" }[level];
  return <span className={cx("sev", level)} role="img" aria-label={name} />;
}

/** Account chip — two-letter mark plus the masked account label. */
export function Src({ mark, children }: { mark: string; children: ReactNode }) {
  return (
    <span className="src">
      <b>{mark}</b>
      {children}
    </span>
  );
}

/* ------------------------------------------------------------------ data */

export function Kpi({
  label,
  value,
  detail,
  valueStyle,
  card = true,
}: {
  label: ReactNode;
  value: ReactNode;
  detail?: ReactNode;
  valueStyle?: React.CSSProperties;
  card?: boolean;
}) {
  return (
    <div className={cx(card && "card", "kpi")}>
      <div className="lab">{label}</div>
      <div className="val" style={valueStyle}>
        {value}
      </div>
      {detail ? <div className="dt">{detail}</div> : null}
    </div>
  );
}

export function Bar({ percent, width, color }: { percent: number; width?: number | string; color?: string }) {
  return (
    <div className="bar" style={width ? { width } : undefined}>
      <i style={{ width: `${Math.max(0, Math.min(100, percent))}%`, background: color }} />
    </div>
  );
}

export function Spark({
  values,
  height = 44,
  style,
}: {
  /** Bar heights as percentages of the track. */
  values: number[];
  height?: number;
  style?: React.CSSProperties;
}) {
  const max = Math.max(...values, 1);
  return (
    <div className="spark" style={{ height, ...style }}>
      {values.map((v, i) => (
        <i key={i} style={{ height: `${Math.max(2, (v / max) * 100)}%` }} />
      ))}
    </div>
  );
}

export function Legend({ items }: { items: ReactNode[] }) {
  return (
    <div className="legend">
      {items.map((item, i) => (
        <span key={i}>{item}</span>
      ))}
    </div>
  );
}

/** Horizontal-scroll box for dense tables so the page body never scrolls. */
export function Tbl({ children }: { children: ReactNode }) {
  return <div className="tbl">{children}</div>;
}

export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <div className="stepper">
      {steps.map((step, i) => (
        <div key={step} className={cx(i === current && "on", i < current && "done")}>
          {i + 1} · {step}
        </div>
      ))}
    </div>
  );
}

export function Ph({
  children,
  height,
  className,
  style,
  ...rest
}: React.HTMLAttributes<HTMLDivElement> & { height?: number | string }) {
  return (
    <div className={cx("ph", className)} style={{ height, ...style }} {...rest}>
      {children}
    </div>
  );
}

export function Hint({ children, style }: { children: ReactNode; style?: React.CSSProperties }) {
  return (
    <div className="hint" style={style}>
      {children}
    </div>
  );
}

export function Mob({ children, caption }: { children: ReactNode; caption?: string }) {
  return (
    <div>
      <div className="mob">
        <div className="bar2" />
        <div style={{ padding: 16 }}>{children}</div>
      </div>
      {caption ? <div className="hint" style={{ textAlign: "center", marginTop: 7 }}>{caption}</div> : null}
    </div>
  );
}

/* ----------------------------------------------------------------- forms */

export function Field({
  label,
  hint,
  error,
  optional,
  children,
  id,
}: {
  label?: ReactNode;
  hint?: ReactNode;
  error?: string;
  optional?: boolean;
  children: ReactNode;
  id?: string;
}) {
  return (
    <div className="field">
      {label ? (
        <label htmlFor={id}>
          {label}
          {optional ? <span style={{ fontWeight: 400, color: "var(--ink3)" }}> optional</span> : null}
        </label>
      ) : null}
      {children}
      {error ? (
        <div className="errmsg" role="alert">
          {error}
        </div>
      ) : hint ? (
        <div className="hint">{hint}</div>
      ) : null}
    </div>
  );
}

export function Inp({
  invalid,
  className,
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  return <input className={cx("inp", invalid && "err", className)} aria-invalid={invalid || undefined} {...rest} />;
}

export function Select({
  invalid,
  className,
  children,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & { invalid?: boolean }) {
  return (
    <select className={cx("inp", invalid && "err", className)} {...rest}>
      {children}
    </select>
  );
}

export function Textarea({
  invalid,
  className,
  ...rest
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean }) {
  return <textarea className={cx("inp", invalid && "err", className)} {...rest} />;
}

export function Check({
  label,
  id,
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label: ReactNode }) {
  const auto = useId();
  const inputId = id ?? auto;
  return (
    <label
      htmlFor={inputId}
      style={{ fontSize: 12.5, display: "flex", gap: 8, alignItems: "flex-start", margin: "6px 0", cursor: "pointer" }}
    >
      <input id={inputId} type="checkbox" style={{ marginTop: 2 }} {...rest} />
      <span style={{ color: "var(--ink2)" }}>{label}</span>
    </label>
  );
}

export function Radio({
  label,
  id,
  right,
  boxed,
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label: ReactNode; right?: ReactNode; boxed?: boolean }) {
  const auto = useId();
  const inputId = id ?? auto;
  return (
    <label
      htmlFor={inputId}
      style={{
        fontSize: 12.5,
        display: "flex",
        gap: 8,
        alignItems: "center",
        margin: boxed ? "7px 0" : "8px 0",
        cursor: "pointer",
        ...(boxed
          ? {
              padding: 11,
              border: `1px solid ${rest.checked ? "var(--g500)" : "var(--line)"}`,
              borderRadius: 8,
            }
          : {}),
      }}
    >
      <input id={inputId} type="radio" {...rest} />
      <span>{label}</span>
      {right ? <span style={{ marginLeft: "auto" }}>{right}</span> : null}
    </label>
  );
}

/* ------------------------------------------------------------ page state */

/**
 * Coverage statement. Non-negotiable: it sits above the fold on every
 * consolidated view and prints on every export — never a tooltip or modal.
 */
export function Coverage({
  accounts,
  notes,
  compact = false,
}: {
  accounts: {
    label: string;
    source: string;
    period: string;
    tier: "A" | "B" | "C" | "D";
    audit: ReactNode;
    transactions?: ReactNode;
  }[];
  notes?: ReactNode;
  compact?: boolean;
}) {
  return (
    <Card
      title={compact ? undefined : "What this analysis is based on"}
      sub={compact ? undefined : "Read this before relying on any figure above."}
    >
      {compact ? (
        <div
          style={{
            fontSize: 10,
            textTransform: "uppercase",
            letterSpacing: 0.6,
            fontWeight: 700,
            color: "var(--ink3)",
            marginBottom: 8,
          }}
        >
          Coverage
        </div>
      ) : null}
      <Tbl>
        <table className="stack">
          <thead>
            <tr>
              <th>Account</th>
              <th>Source</th>
              <th>Period covered</th>
              <th>Tier</th>
              <th>Audit</th>
              {accounts.some((a) => a.transactions != null) ? <th className="num">Transactions</th> : null}
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.label}>
                <td data-l="Account">{a.label}</td>
                <td data-l="Source">{a.source}</td>
                <td data-l="Period">{a.period}</td>
                <td data-l="Tier">
                  <Tier tier={a.tier} />
                </td>
                <td data-l="Audit">{a.audit}</td>
                {accounts.some((x) => x.transactions != null) ? (
                  <td className="num" data-l="Transactions">
                    {a.transactions ?? "—"}
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </Tbl>
      {notes ? (
        <div style={{ fontSize: 11, color: "var(--ink3)", marginTop: 8 }}>{notes}</div>
      ) : null}
    </Card>
  );
}

/**
 * Empty state. The prototype's rule: never render zeros as an empty state,
 * and name exactly one next action — not three.
 */
export function Empty({
  icon,
  title,
  children,
  actionLabel,
  onAction,
}: {
  icon?: ReactNode;
  title: string;
  children?: ReactNode;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div style={{ padding: "26px 16px", textAlign: "center", border: "1px dashed var(--line)", borderRadius: 10 }}>
      {icon ? <div style={{ fontSize: 26, marginBottom: 9 }}>{icon}</div> : null}
      <b style={{ fontSize: 13 }}>{title}</b>
      {children ? (
        <div style={{ fontSize: 12, color: "var(--ink2)", marginTop: 6, lineHeight: 1.6 }}>{children}</div>
      ) : null}
      {actionLabel ? (
        <div style={{ marginTop: 13 }}>
          <Btn sm onClick={onAction}>
            {actionLabel}
          </Btn>
        </div>
      ) : null}
    </div>
  );
}

/**
 * Skeleton for a data screen. The prototype forbids a bare spinner anywhere
 * figures will appear — blocks match the size of what is coming so the
 * layout does not jump.
 */
export function SkeletonKpis({ count = 4 }: { count?: number }) {
  return (
    <Row cols={4}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card">
          <div className="sk" style={{ height: 9, width: "52%" }} />
          <div className="sk lg" style={{ height: 20, width: "70%", marginTop: 9 }} />
          <div className="sk" style={{ height: 8, width: "44%", marginTop: 8 }} />
        </div>
      ))}
    </Row>
  );
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div>
      <div className="sk" style={{ height: 9, width: "30%", marginBottom: 12 }} />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="sk txt" style={{ height: 10, width: `${100 - i * 4}%`, marginBottom: 9 }} />
      ))}
    </div>
  );
}

/**
 * Failure state. Never a raw error code, never a lost upload — the copy is
 * fixed by the prototype's loading-and-skeletons screen.
 */
export function LoadFailed({ onRetry, children }: { onRetry?: () => void; children?: ReactNode }) {
  return (
    <Card>
      <div style={{ padding: 13, background: "var(--stopbg)", borderRadius: 8, fontSize: 12.5, color: "#6B2020" }}>
        <b>We could not finish this</b>
        <br />
        {children ?? "Your statements are safe and nothing was lost. Try again, or we will retry automatically in a few minutes."}
      </div>
      {onRetry ? (
        <Btn sm tone="sec" style={{ marginTop: 11 }} onClick={onRetry}>
          Try again
        </Btn>
      ) : null}
    </Card>
  );
}

/* --------------------------------------------------------------- drawer */

/**
 * Drill-down panel. Traceability is structural: every figure opens to the
 * transactions behind it, and it opens as a panel rather than a new page
 * because the user is checking, not navigating away.
 */
export function Drawer({
  open,
  title,
  sub,
  onClose,
  children,
}: {
  open: boolean;
  title: ReactNode;
  sub?: ReactNode;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div className="drawer-scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={typeof title === "string" ? title : "Detail"}>
        <div className="drawer-head">
          <div>
            <h2>{title}</h2>
            {sub ? <div className="hint">{sub}</div> : null}
          </div>
          <Btn tone="gho" sm onClick={onClose}>
            Close
          </Btn>
        </div>
        {children}
      </aside>
    </>
  );
}

/* ----------------------------------------------------------- formatted */

/** Money, or the unavailable chip when the backend could not determine it. */
export function Money({
  value,
  reason,
  decimals = 0,
  currency = "₦",
  signed = false,
  style,
}: {
  value: number | string | null | undefined;
  /** Why the figure is unavailable. Shown on the chip. */
  reason?: string;
  decimals?: number;
  currency?: string;
  /** Show a leading + for positive values (net positions). */
  signed?: boolean;
  style?: React.CSSProperties;
}) {
  const text = money(value, { currency, decimals });
  if (text === null) return <Na reason={reason} />;
  const n = typeof value === "string" ? Number(value) : (value as number);
  return (
    <span style={style}>
      {signed && n > 0 ? "+" : ""}
      {text}
    </span>
  );
}

/** A plain number, or the unavailable chip. Never a zero standing in for one. */
export function Num({
  value,
  suffix,
  decimals = 0,
  reason,
}: {
  value: number | string | null | undefined;
  suffix?: string;
  decimals?: number;
  reason?: string;
}) {
  if (value === null || value === undefined || value === "") return <Na reason={reason} />;
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return <Na reason={reason} />;
  return (
    <>
      {n.toLocaleString("en-NG", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {suffix ? <span style={{ fontSize: 14, fontWeight: 500 }}> {suffix}</span> : null}
    </>
  );
}
