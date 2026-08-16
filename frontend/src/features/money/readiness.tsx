/**
 * My readiness (screen 30) and Financial health playbook (63).
 *
 * Readiness is the same analysis a lender would see, framed as the user's
 * own position — and it is emphatically not a credit score. The endpoint
 * returns a 0–100 loan-readiness score and a tier letter; neither reaches
 * this screen, because PRD rule R5 prohibits any score, grade or rating.
 * What is shown is the underlying evidence, which is what a lender reads.
 *
 * The playbook sorts by urgency then by amount at stake, shows the
 * confidence on every card, and drops any recommendation missing a
 * required field rather than rendering a half-populated one.
 */

import {
  Btn,
  Card,
  Hint,
  LoadFailed,
  Money,
  Na,
  Pill,
  Row,
  SkeletonRows,
  Tbl,
} from "@/components/sw";
import { money } from "@/components/sw/format";
import type { AiRecommendation } from "@/features/dashboard/bank-api";
import {
  useAbm,
  useDashboardSummary,
  useFinancialHealthPlaybook,
  useLoanReadiness,
} from "@/features/dashboard/bank-api";
import { NO_BALANCE_REASON } from "./use-account";

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(n) ? n : null;
}

/* ----------------------------------------------------- screen 30 */

export function ReadinessView({ accountId, onShare }: { accountId: string; onShare: () => void }) {
  const summary = useDashboardSummary(accountId);
  const readiness = useLoanReadiness(accountId);
  const abm = useAbm(accountId);

  if (summary.isLoading || readiness.isLoading) {
    return (
      <Card>
        <SkeletonRows rows={7} />
      </Card>
    );
  }
  if (summary.isError || !summary.data) return <LoadFailed onRetry={() => summary.refetch()} />;

  const trend = summary.data.monthly_cashflow_trend ?? [];
  const avgTurnover = trend.length
    ? trend.reduce((s, m) => s + (num(m.inflow) ?? 0), 0) / trend.length
    : null;
  const sources = summary.data.top_income_sources ?? [];
  const totalIn = num(summary.data.inflows);
  const largestShare = totalIn && sources.length ? ((num(sources[0].total_inflow) ?? 0) / totalIn) * 100 : null;

  const coverage = readiness.data?.estimated_debt_coverage_indicator ?? null;
  const obligations = num(coverage?.estimated_monthly_debt_obligations);
  const dsr = obligations !== null && avgTurnover ? (obligations / avgTurnover) * 100 : null;

  const abmData = abm.data?.data ?? null;

  // A common institutional rule of thumb, stated as such rather than
  // presented as an amount Scanwick is offering or recommending.
  const indicativeSize = avgTurnover !== null ? avgTurnover * 0.4 : null;

  // Things a lender would ask about, derived only from what is measured.
  const questions: string[] = [];
  if (largestShare !== null && largestShare >= 30) {
    questions.push(
      `One payer accounts for ${largestShare.toFixed(1)}% of your income. A lender will ask what happens if they stop.`,
    );
  }
  if (dsr !== null && dsr >= 35) {
    questions.push(`Your existing obligations already take ${dsr.toFixed(1)}% of monthly income.`);
  }
  if (trend.length > 0 && trend.length < 6) {
    questions.push(
      `Only ${trend.length} month${trend.length === 1 ? "" : "s"} of history is covered. Most lenders want six.`,
    );
  }
  if (trend.some((m) => (num(m.inflow) ?? 0) === 0)) {
    questions.push("At least one month in the period shows no income at all.");
  }
  const disabled = readiness.data?.disabled_components ?? [];
  if (disabled.length > 0) {
    questions.push(`These could not be assessed on your statements: ${disabled.join(", ")}.`);
  }

  return (
    <>
      <Card style={{ marginBottom: 16, background: "var(--g50)", borderColor: "var(--g300)" }}>
        <b style={{ fontSize: 13 }}>This is not a credit score, and Scanwick does not produce one.</b>
        <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 5 }}>
          What follows is what a lender would be able to read from your statements. Whether to lend, and how much, is
          entirely their decision.
        </div>
      </Card>

      <Row cols="21">
        <Card title="What a lender would see">
          <Tbl>
            <table className="stack">
              <thead>
                <tr>
                  <th>What they look at</th>
                  <th className="num">Your position</th>
                  <th>How it reads</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td data-l="Measure">Average monthly turnover</td>
                  <td className="num" data-l="Position">
                    <Money value={avgTurnover} reason="Needs a monthly breakdown." />
                  </td>
                  <td data-l="Reads">
                    {trend.length ? `Across ${trend.length} months` : "Not enough history yet"}
                  </td>
                </tr>
                <tr>
                  <td data-l="Measure">Lending sized at ~40% of turnover</td>
                  <td className="num" data-l="Position">
                    <Money value={indicativeSize} reason="Needs an average turnover figure." />
                  </td>
                  <td data-l="Reads">A common institutional rule of thumb, not an offer</td>
                </tr>
                <tr>
                  <td data-l="Measure">Income sources</td>
                  <td className="num" data-l="Position">
                    {sources.length || <Na />}
                  </td>
                  <td data-l="Reads">
                    {largestShare === null
                      ? ""
                      : largestShare < 30
                        ? "Not concentrated in one customer"
                        : `Largest is ${largestShare.toFixed(1)}% of income`}
                  </td>
                </tr>
                <tr>
                  <td data-l="Measure">Existing obligations</td>
                  <td className="num" data-l="Position">
                    <Money value={obligations} reason="No monthly obligation figure was produced for this run." />
                  </td>
                  <td data-l="Reads">
                    {dsr !== null ? `${dsr.toFixed(1)}% of income — ${dsr < 15 ? "low" : dsr < 35 ? "moderate" : "high"}` : ""}
                  </td>
                </tr>
                <tr>
                  <td data-l="Measure">Average balance</td>
                  <td className="num" data-l="Position">
                    <Money value={abmData?.abm_3m ?? null} reason={NO_BALANCE_REASON} />
                  </td>
                  <td data-l="Reads">{abmData ? `3-month · trend ${abmData.trend}` : ""}</td>
                </tr>
                <tr>
                  <td data-l="Measure">Coverage of the period</td>
                  <td className="num" data-l="Position">
                    {trend.length ? `${trend.length} months` : <Na />}
                  </td>
                  <td data-l="Reads">Every figure above is drawn from this window only</td>
                </tr>
              </tbody>
            </table>
          </Tbl>
        </Card>

        <div>
          <Card title="What would raise a question" style={{ marginBottom: 14 }}>
            {questions.length === 0 ? (
              <div style={{ fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.8 }}>
                Nothing in this analysis stands out as a question a lender would need answered first.
              </div>
            ) : (
              <div style={{ fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.8 }}>
                {questions.map((q) => (
                  <div key={q}>• {q}</div>
                ))}
              </div>
            )}
            <Hint style={{ marginTop: 10 }}>
              Shown so you can answer these before you are asked, not to discourage you.
            </Hint>
          </Card>

          <Card title="Ready to share?" sub="You choose the lender. You can revoke at any time.">
            <Btn block onClick={onShare}>
              Create a share link
            </Btn>
            <Hint style={{ marginTop: 9 }}>
              The recipient sees your analysis, the source tier of every account and the coverage statement — nothing you
              have not granted.
            </Hint>
          </Card>
        </div>
      </Row>
    </>
  );
}

/* ----------------------------------------------------- screen 63 */

const URGENCY = {
  this_week: { label: "This week", tone: "d" as const, rail: "#B91C1C", rank: 0 },
  this_month: { label: "This month", tone: "c" as const, rail: "#D97706", rank: 1 },
  this_quarter: { label: "This quarter", tone: "n" as const, rail: "#9AA6A0", rank: 2 },
};

/** Every field the schema requires must be present or the card is dropped. */
function isComplete(r: AiRecommendation): boolean {
  return Boolean(
    r.trigger_condition &&
      r.entity_type &&
      r.entity_name &&
      r.recommended_action &&
      r.reasoning &&
      r.urgency &&
      typeof r.confidence_score === "number" &&
      typeof r.revenue_at_stake === "number",
  );
}

export function PlaybookView({ accountId }: { accountId: string }) {
  const playbook = useFinancialHealthPlaybook(accountId);

  if (playbook.isLoading) {
    return (
      <Card>
        <SkeletonRows rows={6} />
      </Card>
    );
  }
  if (playbook.isError) return <LoadFailed onRetry={() => playbook.refetch()} />;

  const all = playbook.data?.recommendations ?? [];
  const usable = all.filter(isComplete).sort((a, b) => {
    const rank = (URGENCY[a.urgency]?.rank ?? 9) - (URGENCY[b.urgency]?.rank ?? 9);
    return rank !== 0 ? rank : b.revenue_at_stake - a.revenue_at_stake;
  });
  const dropped = all.length - usable.length;

  return (
    <>
      <Row cols="21">
        <Card title="Recommendations" sub="Each carries its trigger, the amount at stake, a confidence and an urgency">
          {usable.length === 0 ? (
            <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>
              Nothing in this analysis meets the threshold for a recommendation.
            </div>
          ) : (
            usable.map((r) => {
              const urgency = URGENCY[r.urgency] ?? URGENCY.this_quarter;
              return (
                <div
                  key={r.id}
                  style={{
                    border: "1px solid var(--line)",
                    borderLeft: `4px solid ${urgency.rail}`,
                    borderRadius: 8,
                    padding: 15,
                    marginBottom: 12,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: 14,
                      flexWrap: "wrap",
                    }}
                  >
                    <div>
                      <Pill tone={urgency.tone}>{urgency.label}</Pill>{" "}
                      <b style={{ fontSize: 13.5, marginLeft: 6 }}>{r.recommended_action}</b>
                      <Hint style={{ marginTop: 4 }}>
                        {r.entity_type} · {r.entity_name}
                      </Hint>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div className="lab" style={{ fontSize: 10, color: "var(--ink3)", fontWeight: 700 }}>
                        AT STAKE
                      </div>
                      <div style={{ fontSize: 16, fontWeight: 700 }}>
                        {money(r.revenue_at_stake, { currency: r.currency === "NGN" ? "₦" : `${r.currency} ` })}
                      </div>
                    </div>
                  </div>

                  <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 10 }}>
                    <b>Triggered by:</b> {r.trigger_condition}
                  </div>
                  <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 7 }}>
                    <b>Why:</b> {r.reasoning}
                  </div>

                  <div
                    style={{
                      marginTop: 11,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 12,
                    }}
                  >
                    <Hint>Confidence {r.confidence_score.toFixed(2)}</Hint>
                    {/* Confidence is shown, never hidden — a 0.64 must not
                        look as certain as a 0.91. */}
                    <div style={{ width: 90 }}>
                      <div className="bar">
                        <i
                          style={{
                            width: `${Math.round(r.confidence_score * 100)}%`,
                            background: r.confidence_score >= 0.8 ? "var(--g500)" : "var(--g300)",
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </Card>

        <Card title="This analysis">
          <table>
            <tbody>
              <tr>
                <td>Recommendations</td>
                <td className="num">{usable.length}</td>
              </tr>
              <tr>
                <td>Highest urgency</td>
                <td className="num">
                  {usable.length ? (URGENCY[usable[0].urgency]?.label ?? "—") : "—"}
                </td>
              </tr>
              <tr>
                <td>Total at stake</td>
                <td className="num">
                  {money(usable.reduce((sum, r) => sum + r.revenue_at_stake, 0)) ?? "—"}
                </td>
              </tr>
            </tbody>
          </table>
          {dropped > 0 ? (
            <Hint style={{ marginTop: 10 }}>
              {dropped} incomplete recommendation{dropped === 1 ? " was" : "s were"} not shown.
            </Hint>
          ) : null}
        </Card>
      </Row>
    </>
  );
}
