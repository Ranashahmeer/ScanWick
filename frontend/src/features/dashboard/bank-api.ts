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

async function getByAccount<T>(path: string, accountId: string): Promise<Envelope<T>> {
  const { data } = await apiClient.get<Envelope<T>>(`/bank${path}`, { params: { account_id: accountId } })
  return data
}

// ---- Accounts list ----
export interface BankAccount {
  id: string
  bank_name: string | null
  base_currency: string | null
  statement_period_start: string | null
  statement_period_end: string | null
  closing_balance: string | null
}

export function useBankAccounts(merchantId: string) {
  return useQuery({
    queryKey: ["bank", "accounts", merchantId],
    queryFn: async () => {
      const { data } = await apiClient.get<{ data: BankAccount[] }>("/bank/accounts", { params: { merchant_id: merchantId } })
      return data.data
    },
  })
}

// ---- Dashboard summary ----
export interface DashboardSummary {
  inflows: string
  outflows: string
  balance: { opening: string | null; closing: string | null; net_change: string | null }
  monthly_cashflow_trend: { month: string; inflow: string; outflow: string }[]
  credit_debit_split: { credit_count: number; debit_count: number; credit_pct: number; debit_pct: number }
  top_payees_by_outflow: { payee: string; total_outflow: string; occurrence_count: number }[]
  top_income_sources: { payee: string; total_inflow: string; occurrence_count: number }[]
  _analysisRunId: string | null
}

export function useDashboardSummary(accountId: string) {
  return useQuery({
    queryKey: ["bank", "dashboard-summary", accountId],
    queryFn: () =>
      getByAccount<Omit<DashboardSummary, "_analysisRunId">>("/dashboard/summary", accountId).then((e) => ({
        ...e.data,
        _analysisRunId: e.meta.analysis_run_id,
      })),
    enabled: !!accountId,
  })
}

// ---- Income stability (can be disabled: data === null) ----
export interface IncomeStability {
  score: number
  label: "stable" | "moderate" | "volatile"
  cv_pct: number
}

export function useIncomeStability(accountId: string) {
  return useQuery({
    queryKey: ["bank", "income-stability", accountId],
    queryFn: () => getByAccount<IncomeStability | null>("/diagnostic/income-stability", accountId),
    enabled: !!accountId,
  })
}

// ---- ABM (can be disabled: data === null) ----
export interface Abm {
  abm_3m: number | null
  abm_6m: number | null
  abm_12m: number | null
  trend: "improving" | "declining" | "stable"
  score: number
}

export function useAbm(accountId: string) {
  return useQuery({
    queryKey: ["bank", "abm", accountId],
    queryFn: () => getByAccount<Abm | null>("/diagnostic/abm", accountId),
    enabled: !!accountId,
  })
}

// ---- Cashflow analysis ----
export interface CashflowAnalysis {
  cash_buffer_months: number | null
  expense_concentration_ratio_pct: number | null
  recurring_vs_variable: { recurring_total: string; variable_total: string; recurring_pct: number | null; variable_pct: number | null }
  by_payment_mode: { mode: string; total_amount: string; occurrence_count: number }[]
  business_vs_personal: { category: string; total_amount: string; occurrence_count: number }[]
}

export function useCashflowAnalysis(accountId: string) {
  return useQuery({
    queryKey: ["bank", "cashflow-analysis", accountId],
    queryFn: () => getByAccount<CashflowAnalysis>("/diagnostic/cashflow-analysis", accountId).then((e) => e.data),
    enabled: !!accountId,
  })
}

// ---- Fraud risk ----
export interface FraudFlag {
  flag_type: "z_score_anomaly" | "structuring" | "duplicate_payee" | "timing_anomaly"
  description?: string
  transaction_id?: string | null
  amount?: string
  severity: "low" | "medium" | "high"
  z_score?: number
  affected_transaction_count?: number
  duplicate_count?: number
  days_between?: number
}
export interface FraudRisk {
  fraud_risk_score: number
  risk_level: "low" | "medium" | "high" | "critical"
  flags: FraudFlag[]
  statement_integrity: {
    balance_check: "passed" | "failed" | "not_checked"
    date_continuity: "passed" | "failed"
    sequential_ordering: "passed" | "failed"
  }
  score_breakdown: {
    z_score_flags_weight: number
    structuring_flags_weight: number
    duplicate_payee_weight: number
    timing_anomaly_weight: number
  }
}

export function useFraudRisk(accountId: string) {
  return useQuery({
    queryKey: ["bank", "fraud-risk", accountId],
    queryFn: () => getByAccount<FraudRisk>("/predictive/fraud-risk", accountId).then((e) => e.data),
    enabled: !!accountId,
  })
}

// ---- Loan readiness ----
export interface LoanReadiness {
  loan_readiness_score: number
  creditworthiness_tier: "A" | "B" | "C" | "D"
  tier_definition: string
  score_breakdown: Record<string, { weight_pct: number; score: number; contribution: number } & Record<string, unknown>>
  disabled_components: string[]
  improvement_recommendations: { factor: string; current_value: string; target_value: string; action: string; estimated_score_gain: number }[]
  estimated_debt_coverage_indicator: {
    estimated_available_income: string
    estimated_monthly_debt_obligations: string
    coverage_ratio: number | null
    methodology_note: string
  }
}

export function useLoanReadiness(accountId: string) {
  return useQuery({
    queryKey: ["bank", "loan-readiness", accountId],
    queryFn: () => getByAccount<LoanReadiness>("/predictive/loan-readiness", accountId).then((e) => e.data),
    enabled: !!accountId,
  })
}

// ---- Cashflow forecast ----
export interface CashflowForecast {
  forecast_days: number
  base_date: string
  daily_forecast: { date: string; projected_balance: string; confidence_lower_80: string; confidence_upper_80: string }[]
  cash_runway: { primary_scenario_months: number | null; stress_scenario_months: number | null; stress_assumption: string }
  recurring_commitments_projected: { payee: string; amount: string; expected_dates: string[] }[]
}

export function useCashflowForecast(accountId: string) {
  return useQuery({
    queryKey: ["bank", "cashflow-forecast", accountId],
    queryFn: () => getByAccount<CashflowForecast>("/predictive/cashflow-forecast", accountId).then((e) => e.data),
    enabled: !!accountId,
  })
}

// ---- AI recommendation shape (shared across lender-brief + health-playbook) ----
export interface AiRecommendation {
  id: string
  trigger_condition: string
  entity_type: string
  entity_id: string
  entity_name: string
  revenue_at_stake: number
  currency: string
  recommended_action: string
  reasoning: string
  confidence_score: number
  urgency: "this_week" | "this_month" | "this_quarter"
  created_at: string
}

// ---- Lender brief ----
export interface LenderBrief {
  sections: {
    business_overview: { bank_name: string | null; transactions_analyzed: number; statement_period_start: string | null; statement_period_end: string | null }
    income_stability: IncomeStability | null
    cash_flow_analysis: CashflowAnalysis & { abm_trend: Abm | null }
    loan_readiness_assessment: LoanReadiness
    risk_flags: { risk_level: string; fraud_risk_score: number; flag_count: number; statement_integrity: FraudRisk["statement_integrity"] }
    lender_recommendation: AiRecommendation[]
  }
  key_metrics: {
    loan_readiness_score: number
    creditworthiness_tier: string
    fraud_risk_score: number
    income_stability_score: number | null
    cash_buffer_months: number | null
  }
  data_source_footnote: string
  pdf_url: string
}

export function useLenderBrief(accountId: string) {
  return useQuery({
    queryKey: ["bank", "lender-brief", accountId],
    queryFn: () => getByAccount<LenderBrief>("/ai/lender-brief", accountId).then((e) => e.data),
    enabled: !!accountId,
  })
}

// ---- Financial health playbook ----
export interface FinancialHealthPlaybook {
  recommendations: AiRecommendation[]
}

export function useFinancialHealthPlaybook(accountId: string) {
  return useQuery({
    queryKey: ["bank", "health-playbook", accountId],
    queryFn: () => getByAccount<FinancialHealthPlaybook>("/ai/financial-health-playbook", accountId).then((e) => e.data),
    enabled: !!accountId,
  })
}
