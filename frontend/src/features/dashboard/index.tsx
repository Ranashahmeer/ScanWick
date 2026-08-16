/**
 * Home — prototype screen 17.
 *
 * Home is not the consolidated view. The consolidated view is the full
 * analysis; Home is what a returning user needs in ten seconds: what have
 * I got, what is coming, what is broken. An account that reports no balance
 * shows the unavailable chip here too, because the rule holds everywhere.
 */

import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { AppShell, Screen } from "@/features/shell/app-shell";
import {
  Btn,
  Card,
  Empty,
  Hint,
  Legend,
  LoadFailed,
  Money,
  Na,
  Num,
  Row,
  ScreenHead,
  SkeletonKpis,
  SkeletonRows,
  Spark,
  Src,
} from "@/components/sw";
import { fmtDate, fmtDateShort, fmtMonth, money, srcMark } from "@/components/sw/format";
import { useAuth } from "@/hooks/use-auth";
import { useCashflowForecast, useDashboardSummary } from "./bank-api";
import { NO_BALANCE_REASON, useSelectedAccount } from "@/features/money/use-account";

function num(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(n) ? n : null;
}

function greeting(): string {
  const hour = new Date().getHours();
  return hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { accountId, accounts, isLoading, isError, merchantId } = useSelectedAccount();
  const [now] = useState(() => Date.now());

  const summary = useDashboardSummary(accountId ?? "");
  const forecast = useCashflowForecast(accountId ?? "");

  const goto = (to: string, search?: Record<string, string>) =>
    navigate({ to, search: (search ?? {}) as never });

  const firstName = user?.first_name ?? user?.email?.split("@")[0] ?? "there";

  if (!merchantId) {
    return (
      <AppShell>
        <Screen>
          <ScreenHead title="Home" meta="Your daily view" tag="Surface 1" />
          <Card>
            <Empty title="Your account isn't fully set up yet" actionLabel="Sign out and back in" onAction={() => goto("/login")}>
              We could not find a workspace for your user, so there is nothing to show yet.
            </Empty>
          </Card>
        </Screen>
      </AppShell>
    );
  }

  if (isLoading) {
    return (
      <AppShell>
        <Screen>
          <ScreenHead title="Home" meta="Your daily view" tag="Surface 1" />
          <SkeletonKpis count={3} />
        </Screen>
      </AppShell>
    );
  }

  if (isError) {
    return (
      <AppShell>
        <Screen>
          <ScreenHead title="Home" meta="Your daily view" tag="Surface 1" />
          <LoadFailed />
        </Screen>
      </AppShell>
    );
  }

  if (accounts.length === 0 || !accountId) {
    return (
      <AppShell>
        <Screen>
          <ScreenHead title="Home" meta="Your daily view" tag="Surface 1" />
          <Card>
            <Empty icon="🏦" title="Add your first account" actionLabel="Add an account" onAction={() => goto("/accounts")}>
              Connect a bank or wallet, or upload a statement. It takes about a minute and you will see where your money
              went straight away.
            </Empty>
          </Card>
        </Screen>
      </AppShell>
    );
  }

  const withBalance = accounts.filter((a) => num(a.closing_balance) !== null);
  const totalBalance = withBalance.length
    ? withBalance.reduce((sum, a) => sum + (num(a.closing_balance) ?? 0), 0)
    : null;

  const trend = summary.data?.monthly_cashflow_trend ?? [];
  const latest = trend[trend.length - 1] ?? null;
  const latestIn = num(latest?.inflow);
  const latestOut = num(latest?.outflow);
  const latestNet = latestIn !== null && latestOut !== null ? latestIn - latestOut : null;

  const runway = forecast.data?.cash_runway?.primary_scenario_months ?? null;

  // Recurring commitments falling in the next fortnight, which is the
  // "coming up" list the prototype puts second on this screen. The
  // reference time is fixed at mount so "the next 14 days" cannot shift
  // between renders and reorder the list under the reader.
  const fortnight = now + 14 * 86_400_000;
  const upcoming = (forecast.data?.recurring_commitments_projected ?? [])
    .flatMap((c) =>
      (c.expected_dates ?? [])
        .filter((d) => {
          const t = new Date(d).getTime();
          return t >= now && t <= fortnight;
        })
        .map((date) => ({ date, payee: c.payee, amount: num(c.amount) })),
    )
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  const upcomingTotal = upcoming.reduce((sum, u) => sum + (u.amount ?? 0), 0);

  // What is broken. Every account here arrives as an uploaded file, so the
  // thing that goes stale is the statement, not a live connection.
  const stale = accounts.filter((a) => {
    if (!a.statement_period_end) return false;
    const end = new Date(a.statement_period_end).getTime();
    return Number.isFinite(end) && now - end > 45 * 86_400_000;
  });
  const noBalance = accounts.filter((a) => num(a.closing_balance) === null);

  return (
    <AppShell>
      <Screen>
        <ScreenHead title="Home" meta="Where you land · the daily view" tag="Surface 1" />

        <Card style={{ marginBottom: 16, background: "var(--g900)", color: "#fff", border: 0 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 20,
              flexWrap: "wrap",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 11,
                  letterSpacing: ".7px",
                  textTransform: "uppercase",
                  color: "var(--g300)",
                  fontWeight: 700,
                }}
              >
                {greeting()}, {firstName}
              </div>
              <div style={{ fontSize: 23, fontWeight: 700, letterSpacing: "-.6px", marginTop: 5 }}>
                {totalBalance !== null ? (
                  <>
                    You have {money(totalBalance)} across {withBalance.length} account
                    {withBalance.length === 1 ? "" : "s"}
                  </>
                ) : (
                  <>Your {accounts.length}-account analysis is ready</>
                )}
              </div>
              <div style={{ fontSize: 12.5, color: "#CFE0D6", marginTop: 5 }}>
                {noBalance.length > 0
                  ? `${noBalance.length} of your accounts report no balance, so they are not in this figure.`
                  : "All figures are drawn from the statements you have supplied."}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 11, color: "#7FA791" }}>Runway at current rate</div>
              <div style={{ fontSize: 23, fontWeight: 700 }}>
                {runway !== null ? (
                  <Num value={runway} decimals={1} suffix="months" />
                ) : (
                  <span style={{ fontSize: 13 }}>
                    <Na reason="Needs a balance series and an average net outflow." />
                  </span>
                )}
              </div>
            </div>
          </div>
        </Card>

        <Row cols="21" style={{ marginBottom: 16 }}>
          <div>
            <Card
              title="Your latest month"
              sub={latest ? fmtMonth(latest.month) : "No monthly breakdown yet"}
              style={{ marginBottom: 14 }}
            >
              {summary.isLoading ? (
                <SkeletonRows rows={3} />
              ) : summary.isError ? (
                <LoadFailed onRetry={() => summary.refetch()} />
              ) : (
                <>
                  <Row cols={3}>
                    <div className="kpi">
                      <div className="lab">In</div>
                      <div className="val" style={{ fontSize: 21 }}>
                        <Money value={latestIn} reason="No monthly breakdown was returned." />
                      </div>
                    </div>
                    <div className="kpi">
                      <div className="lab">Out</div>
                      <div className="val" style={{ fontSize: 21 }}>
                        <Money value={latestOut} reason="No monthly breakdown was returned." />
                      </div>
                    </div>
                    <div className="kpi">
                      <div className="lab">Net</div>
                      <div
                        className="val"
                        style={{
                          fontSize: 21,
                          color: latestNet === null ? undefined : latestNet >= 0 ? "var(--g600)" : "var(--stop)",
                        }}
                      >
                        <Money value={latestNet} signed />
                      </div>
                    </div>
                  </Row>
                  {trend.length > 0 ? (
                    <>
                      <Spark values={trend.map((m) => num(m.inflow) ?? 0)} height={60} style={{ marginTop: 14 }} />
                      <Legend items={trend.map((m) => fmtMonth(m.month))} />
                    </>
                  ) : null}
                </>
              )}
            </Card>

            <Card title="Coming up" sub="Recurring payments due in the next 14 days">
              {forecast.isLoading ? (
                <SkeletonRows rows={4} />
              ) : upcoming.length === 0 ? (
                <Hint>No recurring payment is projected in the next fortnight.</Hint>
              ) : (
                <>
                  <table>
                    <tbody>
                      {upcoming.map((u, i) => (
                        <tr key={`${u.payee}-${u.date}-${i}`}>
                          <td style={{ whiteSpace: "nowrap" }}>{fmtDateShort(u.date)}</td>
                          <td>{u.payee}</td>
                          <td className="num">
                            <Money value={u.amount} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div
                    style={{
                      marginTop: 12,
                      padding: 11,
                      background: totalBalance !== null && upcomingTotal > totalBalance ? "var(--warnbg)" : "var(--g50)",
                      borderRadius: 8,
                      fontSize: 12.5,
                      color: totalBalance !== null && upcomingTotal > totalBalance ? "#5C4A16" : "var(--ink2)",
                    }}
                  >
                    {money(upcomingTotal)} due in the next 14 days
                    {totalBalance !== null ? ` against a current balance of ${money(totalBalance)}.` : "."}
                  </div>
                </>
              )}
            </Card>
          </div>

          <div>
            {stale.length > 0 || noBalance.length > 0 ? (
              <Card title="Needs your attention" style={{ marginBottom: 14, borderLeft: "4px solid var(--warn)" }}>
                <table>
                  <tbody>
                    {stale.map((a) => (
                      <tr key={a.id}>
                        <td>
                          <b>{a.bank_name ?? "Account"} needs a fresh statement</b>
                          <Hint>Nothing since {fmtDate(a.statement_period_end)}</Hint>
                        </td>
                        <td>
                          <Btn sm onClick={() => goto("/upload")}>
                            Upload
                          </Btn>
                        </td>
                      </tr>
                    ))}
                    {noBalance.map((a) => (
                      <tr key={`${a.id}-nb`}>
                        <td>
                          {a.bank_name ?? "Account"} reports no balance
                          <Hint>Balance metrics for this account show as unavailable</Hint>
                        </td>
                        <td>
                          <Btn sm tone="gho" onClick={() => goto("/money", { view: "coverage" })}>
                            Why
                          </Btn>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            ) : null}

            <Card title="Your accounts" style={{ marginBottom: 14 }}>
              <table>
                <tbody>
                  {accounts.map((a) => (
                    <tr key={a.id}>
                      <td>
                        <Src mark={srcMark(a.bank_name)}>{a.bank_name ?? "Account"}</Src>
                      </td>
                      <td className="num">
                        {num(a.closing_balance) !== null ? (
                          money(num(a.closing_balance))
                        ) : (
                          <Na reason={NO_BALANCE_REASON} label="n/a" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <Btn tone="sec" sm block style={{ marginTop: 12 }} onClick={() => goto("/accounts")}>
                Add an account
              </Btn>
            </Card>

            <Card title="Jump to">
              <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                <Btn tone="gho" sm style={{ justifyContent: "flex-start" }} onClick={() => goto("/money", { view: "spending" })}>
                  Where my money went
                </Btn>
                <Btn tone="gho" sm style={{ justifyContent: "flex-start" }} onClick={() => goto("/money", { view: "payees" })}>
                  Who I pay the most
                </Btn>
                <Btn tone="gho" sm style={{ justifyContent: "flex-start" }} onClick={() => goto("/money", { view: "readiness" })}>
                  Am I ready to borrow?
                </Btn>
                <Btn tone="gho" sm style={{ justifyContent: "flex-start" }} onClick={() => goto("/reports")}>
                  Download a report
                </Btn>
              </div>
            </Card>
          </div>
        </Row>
      </Screen>
    </AppShell>
  );
}
