import { useState } from "react";
import { useScanwickChrome } from "@/features/landing/chrome";
import { useAuth } from "@/hooks/use-auth";
import { IntelligenceSidebar } from "@/features/intelligence/components/sidebar";
import { IntelligenceTopbar } from "@/features/intelligence/components/topbar";
import { PlanUpgradeLockedPage, LimitedAccessBanner } from "@/features/intelligence/components/shared";
import { useSubscription } from "@/features/account/billing/payments-api";
import { usePlanPermissions, getFeatureAccess } from "@/features/account/billing/payments-api";
import { CommerceDashboardPage } from "./pages/commerce-dashboard";
import { sectionGroups, sectionFeatureKeys, sectionLabels, type CommerceSectionId } from "./sections";

export default function CommerceIntelligence() {
  const { theme, toggleTheme } = useScanwickChrome();
  const { user } = useAuth();
  const merchantId = user?.merchant_id ?? null;
  const [activeSection, setActiveSection] = useState<CommerceSectionId>("commerce-dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const { data: subscription } = useSubscription();
  const { data: permissions } = usePlanPermissions();
  const tier = subscription?.tier ?? "free";
  const activeAccess = getFeatureAccess(permissions, sectionFeatureKeys[activeSection], tier);

  return (
    <main className={`scanwick-page fi-shell ${theme === "light" ? "theme-light" : ""}`}>
      <IntelligenceTopbar
        theme={theme}
        onToggleTheme={toggleTheme}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
        dateRangeLabel="Live data"
        moduleLabel="Commerce Intelligence"
      />
      <div className="fi-body">
        <IntelligenceSidebar
          title="Commerce Intelligence"
          groups={sectionGroups.map((group) => ({
            items: group.items.map((item) => ({
              ...item,
              locked: getFeatureAccess(permissions, item.featureKey, tier)?.level === "none",
            })),
          }))}
          open={sidebarOpen}
          activeSection={activeSection}
          onSelect={(id) => setActiveSection(id as CommerceSectionId)}
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
            {!merchantId ? (
              <p className="fi-card-note">Your account isn't fully set up yet. Please sign out and back in.</p>
            ) : activeAccess?.level === "none" ? (
              <PlanUpgradeLockedPage label={sectionLabels[activeSection]} />
            ) : (
              <CommerceDashboardPage merchantId={merchantId} />
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
