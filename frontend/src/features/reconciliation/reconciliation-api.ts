import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"

export interface ReconciliationReportData {
  id: string
  merchant_id: string
  analyzer_type: "ecommerce" | "bank"
  source_file_id: string | null
  date_range_start: string | null
  date_range_end: string | null
  base_currency: string | null
  exchange_rate_source: string | null
  records_analyzed: number | null
  records_excluded: number | null
  exclusion_detail: { reason: string; count: number; value: string }[]
  disabled_features: { feature_name: string; reason: string; data_needed: string }[]
  contextual_markers_applied: unknown[]
  created_at: string | null
}

export function useReconciliationReport(analysisRunId: string | null) {
  return useQuery({
    queryKey: ["reconciliation", analysisRunId],
    queryFn: async () => {
      const { data } = await apiClient.get<{ data: ReconciliationReportData }>(`/reconciliation/${analysisRunId}`)
      return data.data
    },
    enabled: !!analysisRunId,
  })
}
