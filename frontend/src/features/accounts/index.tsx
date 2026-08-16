/**
 * Accounts — prototype screens 06 (add accounts), 15 (connection health)
 * and 16 (disconnected).
 *
 * Screen 15 exists because a connection is not permanent: banks expire
 * tokens, and a borrower can revoke access from their own banking app at
 * any time. If a lapse is not surfaced clearly, monitoring silently stops
 * and everyone assumes it is still running.
 *
 * Every account in the system today arrives as an uploaded file, so what
 * goes stale here is the statement rather than a live token. That is stated
 * on screen rather than dressed up as a live connection.
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
  Pill,
  Row,
  ScreenHead,
  SkeletonRows,
  Src,
  Tbl,
  Tier,
} from "@/components/sw";
import { fmtDate, srcMark } from "@/components/sw/format";
import { SourceHub } from "@/features/upload/components/ingestion-panels";
import { BANK_SOURCES } from "@/features/upload/sources";
import { useSelectedAccount } from "@/features/money/use-account";

export type AccountsView = "add" | "health";

const STALE_DAYS = 45;

function daysSince(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return null;
  return Math.floor((Date.now() - t) / 86_400_000);
}

export function AccountsPage({ view = "add" }: { view?: AccountsView }) {
  const navigate = useNavigate();
  const { accounts, isLoading, isError } = useSelectedAccount();

  const goto = (to: string, search?: Record<string, string>) =>
    navigate({ to, search: (search ?? {}) as never });

  if (view === "health") {
    return (
      <AppShell>
        <Screen>
          <ScreenHead
            title="Connection health"
            meta="A statement that has gone stale is not current data · you and any lender need to see this"
            tag="Accounts"
          />
          <ConnectionHealth
            accounts={accounts}
            isLoading={isLoading}
            isError={isError}
            onUpload={() => goto("/upload")}
          />
        </Screen>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <Screen>
        <ScreenHead
          title="Add accounts"
          meta="13 sources · connect by API where available, upload a file otherwise"
          tag="Ingestion"
          action={
            <Btn sm tone="sec" onClick={() => goto("/accounts", { view: "health" })}>
              Connection health
            </Btn>
          }
        />

        <Row cols="21" style={{ marginBottom: 16 }}>
          <SourceHub
            sources={BANK_SOURCES}
            onUpload={() => goto("/upload")}
            onConnect={() => goto("/upload")}
          />
        </Row>

        <Card title="Added" sub={`${accounts.length} account${accounts.length === 1 ? "" : "s"} in your analysis`}>
          {isLoading ? (
            <SkeletonRows rows={3} />
          ) : accounts.length === 0 ? (
            <Empty
              icon="🏦"
              title="No account yet"
              actionLabel="Upload your first statement"
              onAction={() => goto("/upload")}
            >
              Pick a source above, or upload a statement directly. It takes about a minute.
            </Empty>
          ) : (
            <Tbl>
              <table className="stack">
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Method</th>
                    <th>Period covered</th>
                    <th>Tier</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((account) => (
                    <tr key={account.id}>
                      <td data-l="Account">
                        <Src mark={srcMark(account.bank_name)}>{account.bank_name ?? "Account"}</Src>
                      </td>
                      <td data-l="Method">File upload</td>
                      <td data-l="Period" className="mono">
                        {account.statement_period_start && account.statement_period_end
                          ? `${account.statement_period_start} – ${account.statement_period_end}`
                          : "Period not stated"}
                      </td>
                      <td data-l="Tier">
                        <Tier tier="B" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Tbl>
          )}
          <Btn sm block style={{ marginTop: 12 }} onClick={() => goto("/dashboard")}>
            Continue
          </Btn>
        </Card>
      </Screen>
    </AppShell>
  );
}

/* ------------------------------------------------------ screens 15/16 */

function ConnectionHealth({
  accounts,
  isLoading,
  isError,
  onUpload,
}: {
  accounts: ReturnType<typeof useSelectedAccount>["accounts"];
  isLoading: boolean;
  isError: boolean;
  onUpload: () => void;
}) {
  if (isLoading) return <SkeletonRows rows={5} />;
  if (isError) return <LoadFailed />;

  const rows = accounts.map((account) => {
    const age = daysSince(account.statement_period_end);
    const state = age === null ? "unknown" : age > STALE_DAYS * 2 ? "stale" : age > STALE_DAYS ? "ageing" : "current";
    return { account, age, state };
  });

  const current = rows.filter((r) => r.state === "current").length;
  const ageing = rows.filter((r) => r.state === "ageing").length;
  const stale = rows.filter((r) => r.state === "stale").length;
  const lapsed = rows.filter((r) => r.state === "stale");

  return (
    <>
      <Row cols={4} style={{ marginBottom: 16 }}>
        <Kpi label="Current" value={current} detail="within the last 45 days" valueStyle={{ color: "var(--g600)" }} />
        <Kpi
          label="Needs attention"
          value={ageing}
          detail="a fresh statement is due"
          valueStyle={ageing > 0 ? { color: "var(--warn)" } : undefined}
        />
        <Kpi
          label="Out of date"
          value={stale}
          detail="analysis no longer reflects now"
          valueStyle={stale > 0 ? { color: "var(--stop)" } : undefined}
        />
        <Kpi label="Upload-only" value={accounts.length} detail="cannot be monitored" />
      </Row>

      <Card title="Your accounts" sub="Monitoring depends on these staying current" style={{ marginBottom: 16 }}>
        {accounts.length === 0 ? (
          <Empty title="No account to check" actionLabel="Add an account" onAction={onUpload}>
            Add an account and its freshness will be tracked here.
          </Empty>
        ) : (
          <Tbl>
            <table className="stack">
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Method</th>
                  <th>Covers up to</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map(({ account, age, state }) => (
                  <tr
                    key={account.id}
                    style={
                      state === "stale"
                        ? { background: "var(--stopbg)" }
                        : state === "ageing"
                          ? { background: "var(--warnbg)" }
                          : undefined
                    }
                  >
                    <td data-l="Account">
                      <Src mark={srcMark(account.bank_name)}>{account.bank_name ?? "Account"}</Src>
                    </td>
                    <td data-l="Method">File upload</td>
                    <td data-l="Covers up to" className="num">
                      {fmtDate(account.statement_period_end) ?? "Not stated"}
                    </td>
                    <td data-l="Status">
                      {state === "current" ? (
                        <Pill tone="a">Current</Pill>
                      ) : state === "ageing" ? (
                        <>
                          <Pill tone="c">Statement due</Pill>
                          <Hint>{age} days since the period ended</Hint>
                        </>
                      ) : state === "stale" ? (
                        <>
                          <Pill tone="d">Out of date</Pill>
                          <Hint>{age} days since the period ended</Hint>
                        </>
                      ) : (
                        <>
                          <Pill tone="n">Period not stated</Pill>
                          <Hint>the file did not print a statement period</Hint>
                        </>
                      )}
                    </td>
                    <td>
                      <Btn sm tone={state === "current" ? "gho" : "primary"} onClick={onUpload}>
                        {state === "current" ? "Refresh" : "Upload"}
                      </Btn>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Tbl>
        )}
      </Card>

      {lapsed.length > 0 ? (
        <Row cols={2}>
          <Card title="What this means for you" sub="In-app and by email">
            <div
              style={{
                padding: 14,
                border: "1px solid #E9C6C6",
                borderLeft: "4px solid var(--stop)",
                borderRadius: 8,
                background: "var(--stopbg)",
              }}
            >
              <b style={{ fontSize: 12.5, color: "var(--stop)" }}>
                {lapsed.length === 1
                  ? `Your ${lapsed[0].account.bank_name ?? "account"} data is out of date`
                  : `${lapsed.length} accounts are out of date`}
              </b>
              <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 7 }}>
                Your analysis still covers the period we have, but it does not reflect what has happened since. If a
                lender is relying on this data, they see the same coverage gap you do.
              </div>
              <div style={{ marginTop: 12 }}>
                <Btn sm onClick={onUpload}>
                  Upload a fresh statement
                </Btn>
              </div>
            </div>
            <Hint style={{ marginTop: 11 }}>
              If what you actually want is to withdraw consent, the proper route is the consent centre — not letting data
              go quietly stale.
            </Hint>
          </Card>

          <Card title="What a lender is told" sub="What your lender is told">
            <div style={{ padding: 14, border: "1px solid var(--line)", borderLeft: "4px solid #D97706", borderRadius: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                <span className="sev a" />
                <b style={{ fontSize: 12.5 }}>Monitored account has no recent data</b>
                <Pill tone="c">Act</Pill>
              </div>
              <table style={{ marginTop: 11 }}>
                <tbody>
                  <tr>
                    <td>Accounts affected</td>
                    <td className="num">
                      {lapsed.length} of {accounts.length}
                    </td>
                  </tr>
                  <tr>
                    <td>Coverage now</td>
                    <td className="num">
                      <Pill tone="c">Partial</Pill>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div
                style={{ marginTop: 12, padding: 11, background: "var(--g50)", borderRadius: 8, fontSize: 12.5, color: "var(--ink2)" }}
              >
                <b>Recommended action.</b> Ask for a fresh statement. Until then, any figure covering the recent period is
                computed on partial data and the coverage statement says so.
              </div>
            </div>
            <Hint style={{ marginTop: 11 }}>
              Note what this is not: not an accusation, and not a default event. Statements go stale for ordinary reasons.
            </Hint>
          </Card>
        </Row>
      ) : (
        null
      )}
    </>
  );
}

export default AccountsPage;
