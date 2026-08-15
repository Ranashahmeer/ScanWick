import { useState } from "react";
import { AccountTab } from "./billing/account-tab";
import { SecurityTab } from "./billing/security-tab";
import { SubscriptionTab } from "./billing/subscription-tab";
import { NotificationsTab } from "./billing/notifications-tab";
import { PrivacyTab } from "./billing/privacy-tab";
import type { PaidTier } from "./billing/payments-api";

type BillingSection = "account" | "security" | "subscription" | "notifications" | "privacy";

const tabs: { id: BillingSection; label: string }[] = [
  { id: "account", label: "Account" },
  { id: "security", label: "Login & Security" },
  { id: "subscription", label: "Billing & Subscription" },
  { id: "notifications", label: "Notifications" },
  { id: "privacy", label: "Privacy & Data" },
];

interface AccountBillingProps {
  // Set when arriving via a landing-page "Get Basic"/"Get Premium" CTA
  // (already-authenticated visitor) — lands directly on the Subscription
  // sub-tab and auto-starts checkout for that tier. Arriving with a
  // `?reference=` (Paystack) or `?tx_ref=` (Flutterwave) from a completed
  // checkout redirect also needs the Subscription sub-tab open, even
  // though no upgrade prop is set for that case — checked directly against
  // window.location.search below, since those params belong to the
  // payment provider, not this app's routing.
  initialUpgradeTier?: PaidTier;
}

export function AccountBilling({ initialUpgradeTier }: AccountBillingProps) {
  const [section, setSection] = useState<BillingSection>(() => {
    const returnParams = new URLSearchParams(window.location.search);
    const arrivingFromCheckout =
      initialUpgradeTier || returnParams.has("reference") || returnParams.has("tx_ref");
    return arrivingFromCheckout ? "subscription" : "account";
  });

  return (
    <div>
      <div className="acct-subtabs" role="tablist" aria-label="Account & Billing sections">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={section === tab.id}
            className={`acct-subtab ${section === tab.id ? "is-active" : ""}`}
            onClick={() => setSection(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="acct-stack">
        {section === "account" ? <AccountTab /> : null}
        {section === "security" ? <SecurityTab /> : null}
        {section === "subscription" ? <SubscriptionTab initialUpgradeTier={initialUpgradeTier} /> : null}
        {section === "notifications" ? <NotificationsTab /> : null}
        {section === "privacy" ? <PrivacyTab /> : null}
      </div>
    </div>
  );
}
