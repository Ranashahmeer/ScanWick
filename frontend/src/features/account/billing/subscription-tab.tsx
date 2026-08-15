import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
  useBillingHistory,
  useCancelSubscription,
  useStartCheckout,
  useSubscription,
  useVerifyPayment,
  type PaidTier,
  type SubscriptionTier,
} from "./payments-api";
import { detectLocalCurrency, formatLocalPrice, type LocalPricing } from "@/lib/geo-currency";
import { LoadingLabel } from "@/components/ui/spinner";
import { Skeleton } from "@/components/ui/skeleton";

interface PlanFeatureSet {
  id: SubscriptionTier;
  // Fixed USD reference price — the real source of truth (matches
  // backend/app/config.py's basic_plan_price_usd/premium_plan_price_usd).
  // Displayed converted to the visitor's local currency (geo-currency.ts);
  // the actual checkout charge is always computed server-side in NGN.
  priceUsd: number;
  name: string;
  cadence: string;
  features: string[];
  badge?: string;
}

const plans: PlanFeatureSet[] = [
  {
    id: "free",
    priceUsd: 0,
    name: "Free",
    cadence: "",
    features: [
      "Upload a data quality report",
      "One summary dashboard per module",
      "Monthly trend chart",
    ],
  },
  {
    id: "basic",
    priceUsd: 8.99,
    name: "Basic",
    cadence: "/mo",
    badge: "Most popular",
    features: [
      "Everything in Free",
      "Profit leak, SKU matrix, channels",
      "Pipeline, stage velocity, win/loss",
      "Income stability, fraud risk, loan readiness",
      "Forecasts, KPIs, AI playbooks",
    ],
  },
  {
    id: "premium",
    priceUsd: 16.99,
    name: "Premium",
    cadence: "/mo",
    badge: "Full access",
    features: [
      "Everything in Basic",
      "Inventory forecast, RFM, churn, cohort",
      "Confidence forecast, Win DNA, post-mortem",
      "90-day forecast, lender brief",
      "AI playbooks + explainability, contextual markers",
    ],
  },
];

const TIER_RANK: Record<SubscriptionTier, number> = { free: 0, basic: 1, premium: 2 };

// Reflects a just-completed checkout redirect immediately, before the
// webhook necessarily lands — see payments-api.ts's useVerifyPayment.
//
// Paystack and Flutterwave name their redirect query params differently:
// Paystack appends `?reference=...`, Flutterwave appends `?tx_ref=...`
// (plus `transaction_id`/`status`, which we don't need — verify_transaction
// re-checks the real status with the provider directly rather than trusting
// whatever the redirect URL claims). Our own `provider_reference` is set to
// whichever one the provider that actually processed the charge uses, so
// checking both covers either path transparently.
function usePaymentReturnHandler() {
  const verify = useVerifyPayment();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const reference = params.get("reference") ?? params.get("tx_ref");
    if (!reference) return;

    verify.mutate(reference, {
      onSuccess: (status) => {
        if (status === "success") {
          toast.success("Payment confirmed — your plan is now active.");
        } else if (status === "pending") {
          toast.info("Payment received, still confirming with the provider — this can take a minute.");
        } else {
          toast.error("This payment didn't complete. No changes were made to your plan.");
        }
      },
      onError: () => {
        toast.error("Could not confirm this payment. If you were charged, it will still apply automatically.");
      },
    });

    params.delete("reference");
    params.delete("tx_ref");
    params.delete("transaction_id");
    params.delete("status");
    const next = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
    window.history.replaceState({}, "", next);
    // Runs once, only for a `?reference=`/`?tx_ref=` landed on this page load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

interface SubscriptionTabProps {
  // Set when arriving straight from a landing-page "Get Basic"/"Get
  // Premium" CTA (see AccountBilling) — auto-starts checkout for that tier
  // once, instead of making the visitor click Upgrade a second time after
  // they already told the pricing page which plan they wanted.
  initialUpgradeTier?: PaidTier;
}

export function SubscriptionTab({ initialUpgradeTier }: SubscriptionTabProps) {
  usePaymentReturnHandler();

  const { data: subscription, isLoading } = useSubscription();
  const { data: history } = useBillingHistory();
  const startCheckout = useStartCheckout();
  const cancelSubscription = useCancelSubscription();
  const [confirmingCancel, setConfirmingCancel] = useState(false);
  const autoUpgradeFired = useRef(false);
  const [localPricing, setLocalPricing] = useState<LocalPricing | null>(null);

  useEffect(() => {
    let cancelled = false;
    detectLocalCurrency().then((pricing) => {
      if (!cancelled) setLocalPricing(pricing);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const currentTier: SubscriptionTier = subscription?.tier ?? "free";
  const currentPlan = plans.find((plan) => plan.id === currentTier);
  const isPaid = currentTier !== "free";
  const isCancelling = subscription?.cancel_at_period_end ?? false;

  function startCheckoutFor(tier: PaidTier) {
    startCheckout.mutate(tier, {
      onError: (error) => toast.error(error instanceof Error ? error.message : "Could not start checkout."),
    });
  }

  useEffect(() => {
    if (!initialUpgradeTier || autoUpgradeFired.current || isLoading) return;
    if (initialUpgradeTier === currentTier) return; // already on it — nothing to do
    autoUpgradeFired.current = true;
    startCheckoutFor(initialUpgradeTier);
    // Fires once, only once the current subscription has actually loaded
    // (so it can compare against currentTier and skip a no-op checkout).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialUpgradeTier, isLoading]);

  function handleCancelClick() {
    if (!confirmingCancel) {
      setConfirmingCancel(true);
      return;
    }
    cancelSubscription.mutate(undefined, {
      onSuccess: () => {
        toast.success("Your subscription will end at the close of the current billing period.");
        setConfirmingCancel(false);
      },
      onError: (error) => {
        toast.error(error instanceof Error ? error.message : "Could not cancel your subscription.");
        setConfirmingCancel(false);
      },
    });
  }

  return (
    <>
      <div className="acct-card">
        <div className="acct-plan-header">
          <div>
            <span className="acct-card-hint">Current plan</span>
            {isLoading ? (
              <Skeleton className="h-6 w-24" />
            ) : (
              <strong className="acct-plan-name">{currentPlan?.name}</strong>
            )}
            {isPaid && subscription?.current_period_end ? (
              <span className="acct-muted">
                {isCancelling ? "Ends" : "Renews"} {new Date(subscription.current_period_end).toLocaleDateString()}
              </span>
            ) : (
              <span className="acct-muted">
                {currentPlan ? formatLocalPrice(currentPlan.priceUsd, localPricing) : null}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="acct-card">
        <h2>Plans</h2>
        <p className="acct-card-hint">
          {!localPricing || localPricing.currency === "USD"
            ? "Prices in USD, charged in NGN at checkout."
            : localPricing.currency === "NGN"
              ? "Prices in NGN."
              : `Shown in ${localPricing.currency} for your region — charged in NGN at checkout.`}{" "}
          Payment is handled on our provider's secure page (Paystack, with Flutterwave as an automatic backup) —
          Scanwick never stores your full card number.
        </p>

        <div className="acct-plan-grid">
          {plans.map((plan) => {
            const isCurrent = plan.id === currentTier;
            const isUpgrade = TIER_RANK[plan.id] > TIER_RANK[currentTier];
            const isDowngrade = TIER_RANK[plan.id] < TIER_RANK[currentTier];

            return (
              <div className={`acct-plan-card ${isCurrent ? "is-current" : ""}`} key={plan.id}>
                <div className="acct-plan-card-head">
                  <strong>{plan.name}</strong>
                  {/* Never show a marketing badge ("Most popular"/"Full
                      access") stacked next to "Current" — on the active
                      plan's own card, "Current" is the only status that
                      matters and two green pills next to each other read
                      as ambiguous. */}
                  {plan.badge && !isCurrent ? <span className="acct-plan-badge">{plan.badge}</span> : null}
                  {isCurrent ? (
                    <span className="acct-plan-badge acct-plan-badge-current">Current</span>
                  ) : null}
                </div>
                <div className="acct-plan-price">
                  {formatLocalPrice(plan.priceUsd, localPricing)}
                  <span>{plan.cadence}</span>
                </div>
                <ul>
                  {plan.features.map((feature) => (
                    <li key={feature}>{feature}</li>
                  ))}
                </ul>
                {isCurrent ? (
                  <button type="button" className="acct-btn-outline" disabled>
                    Current plan
                  </button>
                ) : isUpgrade && plan.id !== "free" ? (
                  <button
                    type="button"
                    className="dqr-action-primary"
                    disabled={startCheckout.isPending}
                    onClick={() => startCheckoutFor(plan.id as PaidTier)}
                  >
                    {/* startCheckout.isPending is shared across every card's
                        button (one mutation object) — checking .variables
                        too makes sure only the card actually clicked shows
                        "Redirecting…"; the others just go disabled. */}
                    {startCheckout.isPending && startCheckout.variables === plan.id ? (
                      <LoadingLabel label="Redirecting…" />
                    ) : (
                      "Upgrade"
                    )}
                  </button>
                ) : isDowngrade ? (
                  <button type="button" className="acct-btn-outline" disabled title="Cancel your current plan below to drop to Free — a direct downgrade between paid tiers isn't supported yet.">
                    Cancel to downgrade
                  </button>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>

      <div className="acct-card">
        <h2>Payment method</h2>
        <p className="acct-card-hint">
          Card details are entered and stored on your provider's hosted checkout page, never on Scanwick — there's
          nothing to manage here directly. Starting a new checkout lets you update the card on file.
        </p>
      </div>

      <div className="acct-card">
        <h2>Billing history</h2>
        {!history || history.length === 0 ? (
          <p className="acct-card-hint">No payments yet.</p>
        ) : (
          <div className="acct-table acct-table-4col">
            <div className="acct-table-head">
              <span>Date</span>
              <span>Provider</span>
              <span>Amount</span>
              <span>Status</span>
            </div>
            {history.map((transaction) => (
              <div className="acct-table-row" key={transaction.id}>
                <span>{transaction.created_at ? new Date(transaction.created_at).toLocaleDateString() : "—"}</span>
                <span className="acct-muted" style={{ textTransform: "capitalize" }}>
                  {transaction.provider}
                </span>
                <span>
                  {transaction.currency} {transaction.amount}
                </span>
                <span className="acct-muted" style={{ textTransform: "capitalize" }}>
                  {transaction.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {isPaid ? (
        <div className="acct-card acct-danger-card">
          <h2>Cancel subscription</h2>
          <p className="acct-card-hint">
            {isCancelling
              ? "Your subscription is already set to end at the close of the current billing period."
              : `You'll keep ${currentPlan?.name} access until the end of the current billing period, then drop to Free.`}
          </p>
          {!isCancelling && (
            <button
              type="button"
              className="acct-btn-danger"
              disabled={cancelSubscription.isPending}
              onClick={handleCancelClick}
            >
              {cancelSubscription.isPending ? (
                <LoadingLabel label="Cancelling…" />
              ) : confirmingCancel ? (
                "Click again to confirm cancellation"
              ) : (
                "Cancel subscription"
              )}
            </button>
          )}
        </div>
      ) : null}
    </>
  );
}
