import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { isAxiosError } from "axios"
import { apiClient } from "@/lib/api-client"

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.error?.message === "string") {
    return error.response.data.error.message
  }
  return fallback
}

export class PaymentApiError extends Error {}

interface Envelope<T> {
  success: boolean
  data: T
}

// ---- Subscription ----
export type SubscriptionTier = "free" | "basic" | "premium"
// Only these two are ever checked out — Free is the unpaid default,
// never something you pay for.
export type PaidTier = "basic" | "premium"
export type SubscriptionStatus = "active" | "past_due" | "cancelled" | "incomplete" | null

export interface Subscription {
  tier: SubscriptionTier
  status: SubscriptionStatus
  provider: "paystack" | "flutterwave" | null
  current_period_end: string | null
  cancel_at_period_end: boolean
}

export function useSubscription() {
  return useQuery({
    queryKey: ["payments", "subscription"],
    queryFn: async () => {
      const { data } = await apiClient.get<Envelope<Subscription>>("/payments/subscription")
      return data.data
    },
  })
}

// ---- Billing history ----
export interface PaymentTransaction {
  id: string
  provider: "paystack" | "flutterwave"
  amount: string
  currency: string
  status: "pending" | "success" | "failed"
  created_at: string | null
}

export function useBillingHistory() {
  return useQuery({
    queryKey: ["payments", "history"],
    queryFn: async () => {
      const { data } = await apiClient.get<Envelope<PaymentTransaction[]>>("/payments/history")
      return data.data
    },
  })
}

// ---- Checkout ----
interface CheckoutResult {
  authorization_url: string
  reference: string
}

// Redirects the browser to whichever provider's hosted checkout page
// actually handled this request (Paystack, or Flutterwave if Paystack's
// API call failed — the backend decides, the frontend just follows the URL
// it gets back).
export function useStartCheckout() {
  return useMutation({
    mutationFn: async (tier: PaidTier) => {
      try {
        const { data } = await apiClient.post<Envelope<CheckoutResult>>("/payments/checkout", { tier })
        return data.data
      } catch (error) {
        throw new PaymentApiError(errorMessage(error, "Could not start checkout. Please try again."))
      }
    },
    onSuccess: (result) => {
      window.location.href = result.authorization_url
    },
  })
}

// Called once, on mount, when the browser lands back on the billing tab
// with a `?reference=`/`?tx_ref=` query param from the checkout redirect —
// reflects a successful payment immediately instead of waiting on the
// webhook. The backend applies the tier change synchronously during this
// call, but useSubscription()'s query was already fetched (stale, still
// showing the pre-payment tier) by the time this resolves — without
// invalidating it, the UI would keep showing the old plan until some
// unrelated refetch happened to occur.
export function useVerifyPayment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (reference: string) => {
      const { data } = await apiClient.get<Envelope<{ status: "success" | "pending" | "failed" }>>(
        `/payments/verify/${reference}`
      )
      return data.data.status
    },
    onSuccess: (status) => {
      if (status === "success") {
        queryClient.invalidateQueries({ queryKey: ["payments", "subscription"] })
        queryClient.invalidateQueries({ queryKey: ["payments", "history"] })
      }
    },
  })
}

// ---- Plan permissions matrix ----
// Mirrors backend/app/services/plan_permissions.py — fetched once (long
// staleTime, this is the same data for every user and changes rarely) so
// every vertical shell can look up "does this section belong to this
// user's tier" without hardcoding its own copy of the rules.
export type PlanAccessLevel = "full" | "limited" | "none"

export interface PlanFeatureAccess {
  level: PlanAccessLevel
  detail: string | null
}

export interface PlanFeature {
  key: string
  label: string
  implemented: boolean
  access: Record<SubscriptionTier, PlanFeatureAccess>
}

export type PlanPermissionsMatrix = Record<string, PlanFeature[]>

export function usePlanPermissions() {
  return useQuery({
    queryKey: ["plans", "permissions"],
    queryFn: async () => {
      const { data } = await apiClient.get<Envelope<PlanPermissionsMatrix>>("/plans/permissions")
      return data.data
    },
    staleTime: 60 * 60 * 1000,
  })
}

// Looks up one feature's access for a given tier across every category —
// small enough that a linear scan per lookup is fine (under 70 features
// total), no need to build/maintain a keyed index.
export function getFeatureAccess(
  matrix: PlanPermissionsMatrix | undefined,
  featureKey: string,
  tier: SubscriptionTier
): PlanFeatureAccess | undefined {
  if (!matrix) return undefined
  for (const features of Object.values(matrix)) {
    const feature = features.find((f) => f.key === featureKey)
    if (feature) return feature.access[tier]
  }
  return undefined
}

// ---- Cancel ----
export function useCancelSubscription() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      try {
        await apiClient.post("/payments/cancel")
      } catch (error) {
        throw new PaymentApiError(errorMessage(error, "Could not cancel your subscription. Please try again."))
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payments", "subscription"] })
    },
  })
}
