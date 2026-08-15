import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"

interface Envelope<T> {
  success: boolean
  data: T
  meta: {
    missing_fields: string[]
    disabled_features: { feature_name: string; reason: string; data_needed: string }[]
    analysis_run_id: string | null
  }
}

async function get<T>(path: string, merchantId: string, extraParams: Record<string, string> = {}): Promise<Envelope<T>> {
  const { data } = await apiClient.get<Envelope<T>>(`/ecommerce${path}`, {
    params: { merchant_id: merchantId, ...extraParams },
  })
  return data
}

// ---- Dashboard summary ----
export interface DashboardSummary {
  period: { start: string; end: string }
  gross_revenue: { value: string; currency: string; change_pct: number | null }
  net_revenue: { value: string; currency: string; change_pct: number | null }
  total_orders: number
  avg_order_value: number
  data_freshness: { last_synced: string | null; is_stale: boolean | null }
  _analysisRunId: string | null
}

export function useDashboardSummary(merchantId: string) {
  return useQuery({
    queryKey: ["ecommerce", "dashboard-summary", merchantId],
    queryFn: () =>
      get<Omit<DashboardSummary, "_analysisRunId">>("/dashboard/summary", merchantId).then((e) => ({
        ...e.data,
        _analysisRunId: e.meta.analysis_run_id,
      })),
    enabled: !!merchantId,
  })
}

// ---- Dashboard revenue ----
export interface DashboardRevenue {
  gross_revenue: string
  net_revenue: string
  gap: string
  gap_breakdown: { returns: string; discounts: string; shipping: string; processing: string; ad_spend: string }
  monthly_trend: { month: string; gross: string; net: string }[]
}

export function useDashboardRevenue(merchantId: string) {
  return useQuery({
    queryKey: ["ecommerce", "dashboard-revenue", merchantId],
    queryFn: () => get<DashboardRevenue>("/dashboard/revenue", merchantId).then((e) => e.data),
    enabled: !!merchantId,
  })
}
