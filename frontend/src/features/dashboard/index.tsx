import { useEffect, useState } from "react";
import { useScanwickChrome } from "@/features/landing/chrome";
import { useAuth } from "@/hooks/use-auth";
import { IntelligenceTopbar } from "@/features/intelligence/components/topbar";
import { IntelligenceSidebar } from "@/features/intelligence/components/sidebar";
import { PlanUpgradeLockedPage, LimitedAccessBanner } from "@/features/intelligence/components/shared";
import { useSubscription, usePlanPermissions, getFeatureAccess } from "@/features/account/billing/payments-api";
import { useBankAccounts } from "./bank-api";
import { sectionGroups, sectionFeatureKeys, sectionLabels, type SectionId } from "./sections";
import { FinancialSummaryPage } from "./pages/financial-summary";
import { IncomeStabilityPage } from "./pages/income-stability";
import { AvgMonthlyBalancePage } from "./pages/avg-monthly-balance";
import { CashflowAnalysisPage } from "./pages/cashflow-analysis";
import { FraudRiskPage } from "./pages/fraud-risk";
import { LoanReadinessPage } from "./pages/loan-readiness";
import { CashflowForecastPage } from "./pages/cashflow-forecast";
import { LenderBriefPage } from "./pages/lender-brief";
import { HealthPlaybookPage } from "./pages/health-playbook";

function AccountPicker({
  accounts,
  selectedAccountId,
  onSelect,
}: {
  accounts: { id: string; bank_name: string | null; statement_period_start: string | null; statement_period_end: string | null }[];
  selectedAccountId: string;
  onSelect: (accountId: string) => void;
}) {
  if (accounts.length <= 1) return null;
  return (
    <select
      value={selectedAccountId}
      onChange={(event) => onSelect(event.target.value)}
      style={{
        borderRadius: 7,
        border: "1px solid rgba(88,145,111,0.28)",
        background: "rgba(var(--sw-surface-rgb), 0.6)",
        color: "var(--sw-text-solid)",
        padding: "6px 10px",
        fontSize: 12.5,
        marginLeft: 12,
      }}
    >
      {accounts.map((account) => (
        <option key={account.id} value={account.id}>
          {account.bank_name ?? "Account"} · {account.statement_period_start ?? "—"} to {account.statement_period_end ?? "—"}
        </option>
      ))}
    </select>
  );
}

export default function Dashboard() {
  const { theme, toggleTheme } = useScanwickChrome();
  const { user } = useAuth();
  const merchantId = user?.merchant_id ?? null;
  const [activeSection, setActiveSection] = useState<SectionId>("financial-summary");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);

  const accounts = useBankAccounts(merchantId ?? "");

  const { data: subscription } = useSubscription();
  const { data: permissions } = usePlanPermissions();
  const tier = subscription?.tier ?? "free";
  const activeAccess = getFeatureAccess(permissions, sectionFeatureKeys[activeSection], tier);

  useEffect(() => {
    if (!selectedAccountId && accounts.data && accounts.data.length > 0) {
      setSelectedAccountId(accounts.data[0].id);
    }
  }, [accounts.data, selectedAccountId]);

  if (!merchantId) {
    return (
      <main className={`scanwick-page fi-shell ${theme === "light" ? "theme-light" : ""}`}>
        <p className="fi-card-note">Your account isn't fully set up yet. Please sign out and back in.</p>
      </main>
    );
  }

  return (
    <main className={`scanwick-page fi-shell ${theme === "light" ? "theme-light" : ""}`}>
      <IntelligenceTopbar
        theme={theme}
        onToggleTheme={toggleTheme}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
        dateRangeLabel="Live data"
        moduleLabel="Finance Intelligence"
      />

      {accounts.data && accounts.data.length > 1 && selectedAccountId ? (
        <div style={{ padding: "8px 24px" }}>
          <AccountPicker accounts={accounts.data} selectedAccountId={selectedAccountId} onSelect={setSelectedAccountId} />
        </div>
      ) : null}

      <div className="fi-body">
        <IntelligenceSidebar
          title="Finance Intelligence"
          groups={sectionGroups.map((group) => ({
            title: group.title,
            items: group.items.map((item) => ({
              ...item,
              locked: getFeatureAccess(permissions, item.featureKey, tier)?.level === "none",
            })),
          }))}
          open={sidebarOpen}
          activeSection={activeSection}
          onSelect={(id) => setActiveSection(id as SectionId)}
        />

        <div className="fi-content">
          <div className="fi-content-inner">
            {activeAccess?.level === "limited" ? (
              <LimitedAccessBanner
                detail={activeAccess.detail ?? "Limited view"}
                onAction={() => {
                  window.location.href = "/account?tab=billing";
                }}
              />
            ) : null}
            {accounts.isLoading ? (
              <p className="fi-card-note">Loading accounts…</p>
            ) : accounts.isError ? (
              <p className="fi-card-note">Could not load bank accounts.</p>
            ) : !selectedAccountId ? (
              <p className="fi-card-note">
                No bank statements ingested yet for this merchant. Upload a statement or connect via Mono first.
              </p>
            ) : activeAccess?.level === "none" ? (
              <PlanUpgradeLockedPage label={sectionLabels[activeSection]} />
            ) : activeSection === "financial-summary" ? (
              <FinancialSummaryPage accountId={selectedAccountId} onViewLoanReadiness={() => setActiveSection("loan-readiness")} />
            ) : activeSection === "income-stability" ? (
              <IncomeStabilityPage accountId={selectedAccountId} />
            ) : activeSection === "avg-monthly-balance" ? (
              <AvgMonthlyBalancePage accountId={selectedAccountId} />
            ) : activeSection === "cashflow" ? (
              <CashflowAnalysisPage accountId={selectedAccountId} />
            ) : activeSection === "fraud-risk" ? (
              <FraudRiskPage accountId={selectedAccountId} />
            ) : activeSection === "loan-readiness" ? (
              <LoanReadinessPage accountId={selectedAccountId} />
            ) : activeSection === "90-day-forecast" ? (
              <CashflowForecastPage accountId={selectedAccountId} />
            ) : activeSection === "lender-brief" ? (
              <LenderBriefPage accountId={selectedAccountId} />
            ) : (
              <HealthPlaybookPage accountId={selectedAccountId} />
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
