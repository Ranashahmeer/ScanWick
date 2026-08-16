/**
 * Surface 1 — the individual's own money.
 *
 * One route hosting the prototype's screens 18–31, 63 and 64, selected by
 * the `view` search param so the sidebar can link straight to any of them
 * and the browser's back button works between them.
 *
 * The account picker and the empty state are shared by every view: a screen
 * with no statement behind it shows the one next action, never a dashboard
 * full of zeros.
 */

import { useNavigate } from "@tanstack/react-router";
import { AppShell, Screen } from "@/features/shell/app-shell";
import { Card, Empty, ScreenHead, Select, SkeletonKpis, LoadFailed } from "@/components/sw";
import { useSelectedAccount } from "./use-account";
import { ConsolidatedView, CoverageView } from "./consolidated";
import { FeesView, PayeesView, RecurringView, SpendingView } from "./spending";
import { IncomeView, SeasonalityView, StabilityView } from "./income";
import { BalanceView, ClassifyView, ObligationsView } from "./balance";
import { PlaybookView, ReadinessView } from "./readiness";

export type MoneyView =
  | "consolidated"
  | "coverage"
  | "spending"
  | "payees"
  | "recurring"
  | "fees"
  | "income"
  | "stability"
  | "seasonality"
  | "classify"
  | "balance"
  | "obligations"
  | "playbook"
  | "readiness";

const HEADINGS: Record<MoneyView, { title: string; meta: string }> = {
  consolidated: { title: "Consolidated view", meta: "Every account, one picture" },
  coverage: { title: "Coverage statement", meta: "What your analysis is based on" },
  spending: { title: "Where money goes", meta: "Spending by counterparty · every figure opens to its transactions" },
  payees: { title: "Top payees", meta: "By value, by frequency, and who has gone quiet" },
  recurring: { title: "Recurring outflows", meta: "Detected by amount similarity and interval regularity" },
  fees: { title: "Fees & charges", meta: "The number the bank never adds up" },
  income: { title: "Income & revenue patterns", meta: "Where money comes from, and what shape it has" },
  stability: { title: "Income stability", meta: "How consistent income is, month to month" },
  seasonality: { title: "Seasonality", meta: "Recurring monthly and weekly patterns" },
  classify: { title: "Business vs personal", meta: "Reclassify anything we read differently" },
  balance: { title: "Balance behaviour", meta: "Average, minimum, retention, runway, lowest point" },
  obligations: { title: "Obligations & contributory savings", meta: "What you already owe — and the ajo that counts in your favour" },
  playbook: { title: "Financial health playbook", meta: "What to act on, and by when" },
  readiness: { title: "My readiness", meta: "The same analysis a lender would see, framed as your own position" },
};

export function MoneyPage({ view = "consolidated" }: { view?: MoneyView }) {
  const navigate = useNavigate();
  const { accountId, accounts, isLoading, isError, select, merchantId } = useSelectedAccount();
  const heading = HEADINGS[view] ?? HEADINGS.consolidated;

  const goto = (to: string, search?: Record<string, string>) =>
    navigate({ to, search: (search ?? {}) as never });

  function body() {
    if (!merchantId) {
      return (
        <Card>
          <Empty
            title="Your account isn't fully set up yet"
            actionLabel="Sign out and back in"
            onAction={() => goto("/login")}
          >
            We could not find a workspace for your user, so there is nothing to analyse yet.
          </Empty>
        </Card>
      );
    }

    if (isLoading) return <SkeletonKpis />;
    if (isError) return <LoadFailed />;

    if (accounts.length === 0 || !accountId) {
      return (
        <Card>
          <Empty
            icon="🏦"
            title="Add your first account"
            actionLabel="Add an account"
            onAction={() => goto("/accounts")}
          >
            Connect a bank or wallet, or upload a statement. It takes about a minute and you will see where your money
            went straight away.
          </Empty>
        </Card>
      );
    }

    switch (view) {
      case "coverage":
        return <CoverageView accounts={accounts} />;
      case "spending":
        return <SpendingView accountId={accountId} />;
      case "payees":
        return <PayeesView accountId={accountId} />;
      case "recurring":
        return <RecurringView accountId={accountId} />;
      case "fees":
        return <FeesView accountId={accountId} />;
      case "income":
        return <IncomeView accountId={accountId} />;
      case "stability":
        return <StabilityView accountId={accountId} />;
      case "seasonality":
        return <SeasonalityView accountId={accountId} />;
      case "classify":
        return <ClassifyView accountId={accountId} />;
      case "balance":
        return <BalanceView accountId={accountId} />;
      case "obligations":
        return <ObligationsView accountId={accountId} />;
      case "playbook":
        return <PlaybookView accountId={accountId} />;
      case "readiness":
        return <ReadinessView accountId={accountId} onShare={() => goto("/shares", { view: "create" })} />;
      default:
        return (
          <ConsolidatedView
            accountId={accountId}
            accounts={accounts}
            onAddAccount={() => goto("/accounts")}
          />
        );
    }
  }

  return (
    <AppShell>
      <Screen>
        <ScreenHead
          title={heading.title}
          meta={heading.meta}
          action={
            accounts.length > 1 && accountId ? (
              <Select
                value={accountId}
                onChange={(e) => select(e.target.value)}
                aria-label="Which account"
                style={{ width: "auto", minWidth: 200 }}
              >
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.bank_name ?? "Account"}
                    {a.statement_period_start ? ` · from ${a.statement_period_start}` : ""}
                  </option>
                ))}
              </Select>
            ) : (
              <span className="tag">Surface 1</span>
            )
          }
        />
        {body()}
      </Screen>
    </AppShell>
  );
}

export default MoneyPage;
