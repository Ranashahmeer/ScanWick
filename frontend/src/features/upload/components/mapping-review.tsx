/**
 * Confirm column mapping.
 *
 * Follows the column-mapping design on prototype screen 58: your column,
 * a sample of what it holds, and a select saying what it means. Nothing is
 * guessed silently — a column we could not place defaults to "ignore" and
 * is shown, and the date-convention question is asked rather than inferred,
 * because a file the user exported carries no issuer signature to resolve it
 * from the way a bank statement does.
 */

import { useState } from "react";
import { AppShell, Screen } from "@/features/shell/app-shell";
import { Btn, Card, Hint, Pill, Row, ScreenHead, Select, Stepper, Tbl } from "@/components/sw";
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

export function MappingReviewPage({
  analyzerType,
  mapping,
  confirming,
  errorMessage,
  onConfirm,
  onCancel,
}: {
  analyzerType: "ecommerce" | "bank";
  mapping: MappingDetail;
  confirming: boolean;
  errorMessage: string | null;
  onConfirm: (mapping: Record<string, string>, valueRules: Record<string, string>) => void;
  onCancel: () => void;
}) {
  const fieldOptions = [
    { value: IGNORE_VALUE, label: "Ignore this column" },
    ...CANONICAL_FIELDS[analyzerType].map((field) => ({ value: field, label: fieldLabel(field) })),
  ];

  const reviewHeaders = [
    ...mapping.needs_confirmation.map((n) => ({ userHeader: n.user_header, candidate: n.candidate, prompt: n.prompt })),
    ...mapping.unmapped.map((u) => ({ userHeader: u.user_header, candidate: null as string | null, prompt: u.reason })),
  ];

  const [selections, setSelections] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const row of reviewHeaders) initial[row.userHeader] = row.candidate ?? IGNORE_VALUE;
    return initial;
  });

  const [valueAnswers, setValueAnswers] = useState<Record<string, string>>(() =>
    Object.fromEntries(mapping.value_questions.map((q) => [q.field, q.options[q.options.length - 1] ?? q.options[0]])),
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
    <AppShell>
      <Screen>
        <ScreenHead
          title="Map your columns"
          meta="Tell us what each column means. We remember this for next time."
          tag="Ingestion"
        />
        <Stepper steps={["Add accounts", "Processing", "Review coverage", "Your money"]} current={1} />

        <Row cols="21">
          <div>
            {reviewHeaders.length > 0 ? (
              <Card
                title="Needs your confirmation"
                sub="We could not place these with enough confidence to decide for you"
                style={{ marginBottom: 14 }}
              >
                <Tbl>
                  <table className="stack">
                    <thead>
                      <tr>
                        <th>Your column</th>
                        <th>Why we are asking</th>
                        <th>Means</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reviewHeaders.map((row) => (
                        <tr key={row.userHeader} style={{ background: "var(--warnbg)" }}>
                          <td className="mono" data-l="Your column">
                            {row.userHeader}
                          </td>
                          <td data-l="Why">{row.prompt}</td>
                          <td data-l="Means">
                            <Select
                              value={selections[row.userHeader] ?? IGNORE_VALUE}
                              onChange={(event) =>
                                setSelections((current) => ({ ...current, [row.userHeader]: event.target.value }))
                              }
                              aria-label={`What ${row.userHeader} means`}
                              style={{ padding: "5px 28px 5px 8px", fontSize: 11.5 }}
                            >
                              {fieldOptions.map((option) => (
                                <option key={option.value} value={option.value}>
                                  {option.label}
                                </option>
                              ))}
                            </Select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Tbl>
              </Card>
            ) : null}

            {mapping.value_questions.length > 0 ? (
              <Card
                title="One thing we will not guess"
                sub="A file you exported carries no issuer signature, so the convention cannot be resolved automatically"
                style={{ marginBottom: 14 }}
              >
                {mapping.value_questions.map((question) => (
                  <div key={question.field} className="field">
                    <label>{question.question}</label>
                    <div role="radiogroup" aria-label={question.field} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {question.options.map((option) => (
                        <button
                          key={option}
                          type="button"
                          role="radio"
                          aria-checked={valueAnswers[question.field] === option}
                          className={`btn sm ${valueAnswers[question.field] === option ? "" : "gho"}`}
                          onClick={() => setValueAnswers((current) => ({ ...current, [question.field]: option }))}
                        >
                          {fieldLabel(option)}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </Card>
            ) : null}

            {mapping.auto_mapped.length > 0 ? (
              <Card title="Matched automatically" sub="Shown so you can correct anything we got wrong">
                <Tbl>
                  <table className="stack">
                    <thead>
                      <tr>
                        <th>Your column</th>
                        <th>Maps to</th>
                        <th className="num">How</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mapping.auto_mapped.map((m) => (
                        <tr key={m.user_header}>
                          <td className="mono" data-l="Your column">
                            {m.user_header}
                          </td>
                          <td data-l="Maps to">{fieldLabel(m.canonical)}</td>
                          <td className="num" data-l="How">
                            <Pill tone={m.tier === "exact" ? "a" : "n"}>
                              {m.tier} · {Math.round(m.confidence * 100)}%
                            </Pill>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Tbl>
              </Card>
            ) : null}
          </div>

          <div>
            <Card title="Confirm" style={{ marginBottom: 14 }}>
              {errorMessage ? (
                <div
                  role="alert"
                  style={{
                    padding: "10px 12px",
                    background: "var(--stopbg)",
                    border: "1px solid #E9C6C6",
                    borderRadius: 8,
                    fontSize: 12.5,
                    color: "var(--stop)",
                    marginBottom: 12,
                  }}
                >
                  {errorMessage}
                </div>
              ) : null}
              <Btn block onClick={handleSubmit} disabled={confirming}>
                {confirming ? "Confirming…" : "Confirm and read the file"}
              </Btn>
              <Btn tone="gho" sm block style={{ marginTop: 8 }} onClick={onCancel} disabled={confirming}>
                Cancel
              </Btn>
              <Hint style={{ marginTop: 10 }}>
                Your answers are saved against this source, so the next file you upload from it is mapped without asking
                again.
              </Hint>
            </Card>


          </div>
        </Row>
      </Screen>
    </AppShell>
  );
}
