/**
 * Trading records — prototype screens 58 (connect trading records) and 59
 * (cash-gap verification).
 *
 * Status per the PRD: conditional and unvalidated. No lender has asked for
 * it, it is not a launch dependency, and it must not appear on a lender
 * brief or a shared assessment until one does.
 *
 * Tone is the whole design problem on screen 59. This compares what someone
 * said they earned against what arrived. Framed carelessly it reads as an
 * accusation of lying, and it would be wrong — cash is invisible to a bank
 * statement and cash is a large share of Nigerian retail. Never the words
 * discrepancy, unexplained, missing or shortfall. Never colour the gap red.
 * Say "not matched", give the likely reasons, and lead with the fix.
 */

import { useNavigate } from "@tanstack/react-router";
import { AppShell, Screen } from "@/features/shell/app-shell";
import {
  Btn,
  Card,
  Empty,
  Hint,
  Kpi,
  LoadFailed,
  Money,
  Na,
  Ph,
  Pill,
  Row,
  ScreenHead,
  SkeletonRows,
  Tbl,
} from "@/components/sw";
import { fmtMonth, money } from "@/components/sw/format";
import { useAuth } from "@/hooks/use-auth";
import { useDashboardRevenue, useDashboardSummary as useCommerceSummary } from "./ecommerce-api";
import { useDashboardSummary as useBankSummary } from "@/features/dashboard/bank-api";
import { useSelectedAccount } from "@/features/money/use-account";

export type CommerceView = "connect" | "cash-gap";

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(n) ? n : null;
}

export default function CommerceIntelligence({ view = "connect" }: { view?: CommerceView }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const merchantId = user?.merchant_id ?? null;

  return (
    <AppShell>
      <Screen>
        <ScreenHead
          title={view === "cash-gap" ? "Cash-gap verification" : "Connect trading records"}
          meta={
            view === "cash-gap"
              ? "Did the money you recorded actually arrive?"
              : "Optional · order or sales data compared against bank inflow"
          }
          action={<span className="tag pub">Optional</span>}
        />

        {view === "cash-gap" ? (
          <CashGap merchantId={merchantId} />
        ) : (
          <ConnectRecords onCheck={() => navigate({ to: "/commerce-intelligence", search: { view: "cash-gap" } })} />
        )}
      </Screen>
    </AppShell>
  );
}

/* ---------------------------------------------------------- screen 58 */

function ConnectRecords({ onCheck }: { onCheck: () => void }) {
  const navigate = useNavigate();

  return (
    <Row cols="21">
      <Card
        title="Add your trading records"
        sub="If you sell online or keep order records, we can check whether the money you recorded actually arrived in your accounts."
      >
        <Row cols={3} style={{ gap: 10 }}>
          <Ph
            className="pick"
            height={70}
            style={{ flexDirection: "column", gap: 4 }}
            role="button"
            tabIndex={0}
            onClick={() => navigate({ to: "/upload" })}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") navigate({ to: "/upload" });
            }}
          >
            <b style={{ color: "var(--ink)" }}>CSV export</b>
            <span style={{ fontSize: 10 }}>orders or sales</span>
          </Ph>
          <Ph
            className="pick"
            height={70}
            style={{ flexDirection: "column", gap: 4 }}
            role="button"
            tabIndex={0}
            onClick={() => navigate({ to: "/upload" })}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") navigate({ to: "/upload" });
            }}
          >
            <b style={{ color: "var(--ink)" }}>Spreadsheet</b>
            <span style={{ fontSize: 10 }}>XLS / XLSX</span>
          </Ph>
          <Ph height={70} style={{ flexDirection: "column", gap: 4 }}>
            <b style={{ color: "var(--ink3)" }}>Platform export</b>
            <span style={{ fontSize: 10 }}>later</span>
          </Ph>
        </Row>

        <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn onClick={() => navigate({ to: "/upload" })}>Upload a trading export</Btn>
          <Btn tone="sec" onClick={onCheck}>
            Check against my bank accounts
          </Btn>
        </div>
      </Card>


    </Row>
  );
}

/* ---------------------------------------------------------- screen 59 */

function CashGap({ merchantId }: { merchantId: string | null }) {
  const navigate = useNavigate();
  const commerce = useCommerceSummary(merchantId ?? "");
  const revenue = useDashboardRevenue(merchantId ?? "");
  const { accountId, accounts } = useSelectedAccount();
  const bank = useBankSummary(accountId ?? "");

  if (!merchantId) {
    return (
      <Card>
        <Empty title="Your account isn't fully set up yet">Sign out and back in, then try again.</Empty>
      </Card>
    );
  }

  if (commerce.isLoading || bank.isLoading) {
    return (
      <Card>
        <SkeletonRows rows={6} />
      </Card>
    );
  }

  const recorded = num(commerce.data?.gross_revenue?.value);
  const bankInflow = num(bank.data?.inflows);

  if (recorded === null) {
    return (
      <Card title="Nothing recorded to compare">
        <Empty
          title="No trading records yet"
          actionLabel="Add trading records"
          onAction={() => navigate({ to: "/commerce-intelligence" })}
        >
          Cash-gap verification compares what you recorded as sold against what arrived in the accounts you added. Upload
          an orders export and this fills in.
        </Empty>
      </Card>
    );
  }

  if (commerce.isError) return <LoadFailed onRetry={() => commerce.refetch()} />;

  // Matching is done at the month level, which is the finest grain both
  // sides return. A per-order match would need order references on the
  // bank side, which the statement parsers do not produce.
  const commerceTrend = revenue.data?.monthly_trend ?? [];
  const bankTrend = bank.data?.monthly_cashflow_trend ?? [];
  const bankByMonth = new Map(bankTrend.map((m) => [m.month.slice(0, 7), num(m.inflow) ?? 0]));

  const months = commerceTrend.map((m) => {
    const key = m.month.slice(0, 7);
    const rec = num(m.gross) ?? 0;
    const matched = bankByMonth.get(key) ?? null;
    return {
      month: m.month,
      recorded: rec,
      matched,
      gap: matched === null ? null : rec - matched,
      pct: matched === null || rec === 0 ? null : (matched / rec) * 100,
    };
  });

  const totalMatched = bankInflow;
  const notMatched = totalMatched !== null ? Math.max(0, recorded - totalMatched) : null;
  const matchedPct = totalMatched !== null && recorded > 0 ? (totalMatched / recorded) * 100 : null;

  return (
    <>
      <Row cols={4} style={{ marginBottom: 16 }}>
        <Kpi
          label="Recorded as sold"
          value={<Money value={recorded} />}
          valueStyle={{ fontSize: 22 }}
          detail={commerce.data ? `${commerce.data.total_orders.toLocaleString()} orders` : undefined}
        />
        <Kpi
          label="Arrived in bank"
          value={<Money value={totalMatched} reason="No bank account has been added to compare against." />}
          valueStyle={{ fontSize: 22, color: "var(--g600)" }}
          detail={matchedPct !== null ? `${matchedPct.toFixed(1)}% of recorded value` : undefined}
        />
        <Kpi
          label="Not matched"
          value={<Money value={notMatched} reason="Needs both a recorded figure and a bank inflow figure." />}
          valueStyle={{ fontSize: 22 }}
          detail={
            matchedPct !== null ? `${(100 - matchedPct).toFixed(1)}% · normal where cash sales exist` : undefined
          }
        />
        <Kpi
          label="Accounts compared"
          value={accounts.length}
          valueStyle={{ fontSize: 22 }}
          detail={accounts.length === 0 ? "add one to compare" : "money outside these is invisible"}
        />
      </Row>

      <Row cols="21">
        <Card title="Month by month" sub="Recorded sales against bank inflow in the same month">
          {months.length === 0 ? (
            <Hint>No monthly breakdown was returned on either side, so nothing can be compared month to month.</Hint>
          ) : (
            <Tbl>
              <table className="stack">
                <thead>
                  <tr>
                    <th>Month</th>
                    <th className="num">Recorded</th>
                    <th className="num">Arrived in bank</th>
                    <th className="num">Not matched</th>
                    <th className="num">Matched %</th>
                  </tr>
                </thead>
                <tbody>
                  {months.map((row) => (
                    <tr key={row.month}>
                      <td data-l="Month">{fmtMonth(row.month)}</td>
                      <td className="num" data-l="Recorded">
                        <Money value={row.recorded} />
                      </td>
                      <td className="num" data-l="Arrived">
                        <Money value={row.matched} reason="No bank statement covers this month." />
                      </td>
                      <td className="num" data-l="Not matched">
                        <Money value={row.gap} reason="Needs a bank figure for the same month." />
                      </td>
                      <td className="num" data-l="Matched %">
                        {row.pct !== null ? `${row.pct.toFixed(1)}%` : <Na reason="No bank figure for this month." />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Tbl>
          )}
          <Hint style={{ marginTop: 12 }}>
            Matching is done month by month, which is the finest grain both sides report. A per-order match would need
            order references on the bank side, and bank statements do not carry them.
          </Hint>
        </Card>

        <div>
          <Card title="What this does and does not tell you" style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.75 }}>
              <b>It tells you</b> how much of what you recorded as sold can be traced to money arriving in the accounts
              you added.
              <br />
              <br />
              <b>It does not tell you</b> that anything is wrong. A gap is normal and expected — cash sales leave no bank
              trace at all, some customers pay into accounts you have not added, and some orders are recorded before
              payment clears.
            </div>
            <div style={{ marginTop: 13, padding: 12, background: "var(--g50)", borderRadius: 8, fontSize: 12, color: "var(--ink2)" }}>
              <b>Most common reason for a gap:</b> an account you have not added. Adding it usually closes most of it.
            </div>
            <Btn sm block style={{ marginTop: 11 }} onClick={() => navigate({ to: "/accounts" })}>
              Add another account
            </Btn>
          </Card>

          <Card title="Likely reasons a month does not match">
            <table>
              <tbody>
                <tr>
                  <td>Cash sales</td>
                  <td className="num">
                    <Pill tone="n">No bank record expected</Pill>
                  </td>
                </tr>
                <tr>
                  <td>Paid into an account not added</td>
                  <td className="num">
                    <Pill tone="c">Add the account</Pill>
                  </td>
                </tr>
                <tr>
                  <td>Recorded before payment cleared</td>
                  <td className="num">
                    <Pill tone="n">Timing</Pill>
                  </td>
                </tr>
                <tr>
                  <td>Money arrived that was not an order</td>
                  <td className="num">
                    <Pill tone="n">Expected</Pill>
                  </td>
                </tr>
              </tbody>
            </table>
            <Hint style={{ marginTop: 10 }}>
              A total figure above {money(totalMatched)} in a month simply means money arrived that was not from a
              recorded order — a refund, a transfer, or income from somewhere else.
            </Hint>
          </Card>


        </div>
      </Row>
    </>
  );
}
