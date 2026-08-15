import { ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Table } from "@/features/intelligence/components/shared";
import { AppTopbar } from "./topbar";
import type { MappingDetail } from "../uploads-api";

const IGNORE_VALUE = "__ignore__";

// Mirrors the canonical field keys in backend/app/services/column_mapping.py's
// CANONICAL_SYNONYMS — kept in sync manually since there's no endpoint that
// exposes the full canonical field list on its own (only whichever fields a
// given upload's columns actually became candidates for).
const CANONICAL_FIELDS: Record<"ecommerce" | "bank", string[]> = {
  ecommerce: [
    "external_order_id", "order_date", "gross_revenue", "unit_cogs", "original_currency",
    "discount_amount", "refund_amount", "shipping_cost", "channel", "sku", "quantity",
    "unit_price", "unit_return_cost", "customer_email", "processing_fees", "allocated_ad_spend",
    "category", "payment_method",
  ],
  bank: [
    "transaction_date", "description", "amount", "credit_amount", "debit_amount",
    "transaction_type", "balance_after", "currency", "account_number",
  ],
};

function fieldLabel(field: string): string {
  return field.replace(/_/g, " ");
}

interface FieldOption {
  value: string;
  label: string;
}

// Generalized version of index.tsx's BankSelect (button + listbox, not a
// native <select>) — same interaction pattern, parameterized on an options
// list instead of the hardcoded bank name array.
function FieldSelect({
  value,
  options,
  onChange,
}: {
  value: string;
  options: FieldOption[];
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const selected = options.find((option) => option.value === value);

  return (
    <div className="upload-select" ref={rootRef}>
      <button
        type="button"
        className="upload-select-trigger"
        onClick={() => setOpen((current) => !current)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {selected?.label ?? "Ignore this column"}
        <ChevronDown size={14} strokeWidth={2.4} />
      </button>

      {open ? (
        <ul className="upload-select-menu" role="listbox">
          {options.map((option) => (
            <li
              key={option.value}
              role="option"
              aria-selected={option.value === value}
              className={option.value === value ? "is-selected" : ""}
              onClick={() => {
                onChange(option.value);
                setOpen(false);
              }}
            >
              {option.label}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function MappingReviewPage({
  theme,
  onToggleTheme,
  analyzerType,
  mapping,
  confirming,
  errorMessage,
  onConfirm,
  onCancel,
}: {
  theme: "dark" | "light";
  onToggleTheme: () => void;
  analyzerType: "ecommerce" | "bank";
  mapping: MappingDetail;
  confirming: boolean;
  errorMessage: string | null;
  onConfirm: (mapping: Record<string, string>, valueRules: Record<string, string>) => void;
  onCancel: () => void;
}) {
  const fieldOptions: FieldOption[] = [
    { value: IGNORE_VALUE, label: "Ignore this column" },
    ...CANONICAL_FIELDS[analyzerType].map((field) => ({ value: field, label: fieldLabel(field) })),
  ];

  const reviewHeaders = [
    ...mapping.needs_confirmation.map((n) => ({ userHeader: n.user_header, candidate: n.candidate })),
    ...mapping.unmapped.map((u) => ({ userHeader: u.user_header, candidate: null as string | null })),
  ];

  const [selections, setSelections] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const row of reviewHeaders) initial[row.userHeader] = row.candidate ?? IGNORE_VALUE;
    return initial;
  });

  const [valueAnswers, setValueAnswers] = useState<Record<string, string>>(() =>
    Object.fromEntries(mapping.value_questions.map((q) => [q.field, q.options[q.options.length - 1] ?? q.options[0]]))
  );

  const handleSubmit = () => {
    const finalMapping: Record<string, string> = {};
    for (const auto of mapping.auto_mapped) finalMapping[auto.user_header] = auto.canonical;
    for (const [header, field] of Object.entries(selections)) {
      if (field !== IGNORE_VALUE) finalMapping[header] = field;
    }
    onConfirm(finalMapping, valueAnswers);
  };

  return (
    <main className={`scanwick-page upload-page ${theme === "light" ? "theme-light" : ""}`}>
      <AppTopbar theme={theme} onToggleTheme={onToggleTheme} />

      <section className="upload-main">
        <div className="dqr-inner">
          <div className="upload-heading">
            <h1>Confirm column mapping</h1>
            <p>
              We matched most of your columns automatically. Double-check the ones we weren't
              confident about before we process the file.
            </p>
          </div>

      {mapping.auto_mapped.length > 0 ? (
        <div className="upload-mapping-section">
          <h3>Matched automatically</h3>
          <Table
            columns={[
              { key: "user_header", label: "Your column" },
              { key: "canonical", label: "Maps to" },
              { key: "confidence", label: "Confidence", align: "right" },
            ]}
            rows={mapping.auto_mapped.map((m) => ({
              user_header: m.user_header,
              canonical: fieldLabel(m.canonical),
              confidence: `${m.tier} · ${Math.round(m.confidence * 100)}%`,
            }))}
            rowKey={(row) => String(row.user_header)}
          />
        </div>
      ) : null}

      {reviewHeaders.length > 0 ? (
        <div className="upload-mapping-section">
          <h3>Needs your confirmation</h3>
          <Table
            columns={[
              { key: "user_header", label: "Your column" },
              { key: "select", label: "Maps to" },
            ]}
            rows={reviewHeaders.map((row) => ({
              user_header: row.userHeader,
              select: (
                <FieldSelect
                  value={selections[row.userHeader] ?? IGNORE_VALUE}
                  options={fieldOptions}
                  onChange={(value) => setSelections((current) => ({ ...current, [row.userHeader]: value }))}
                />
              ),
            }))}
            rowKey={(_row, index) => reviewHeaders[index]?.userHeader ?? String(index)}
          />
        </div>
      ) : null}

      {mapping.value_questions.length > 0 ? (
        <div className="upload-mapping-section">
          <h3>One more thing</h3>
          {mapping.value_questions.map((question) => (
            <div key={question.field} className="upload-mapping-value-question">
              <p>{question.question}</p>
              <div className="upload-analyzer-pills" role="radiogroup" aria-label={question.field}>
                {question.options.map((option) => (
                  <button
                    key={option}
                    type="button"
                    role="radio"
                    aria-checked={valueAnswers[question.field] === option}
                    className={`upload-pill ${valueAnswers[question.field] === option ? "is-active" : ""}`}
                    onClick={() => setValueAnswers((current) => ({ ...current, [question.field]: option }))}
                  >
                    {fieldLabel(option)}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {errorMessage ? <p className="upload-mapping-error">{errorMessage}</p> : null}

      <div className="upload-mapping-actions">
        <button type="button" className="upload-choose-another" onClick={onCancel} disabled={confirming}>
          Cancel
        </button>
        <button type="button" className="upload-mono-connect" onClick={handleSubmit} disabled={confirming}>
          {confirming ? "Confirming…" : "Confirm mapping"}
        </button>
      </div>
        </div>
      </section>
    </main>
  );
}
