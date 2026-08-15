import { isAxiosError } from "axios"
import { apiClient } from "@/lib/api-client"

export interface UploadWarning {
  field: string
  severity: string
  message: string
  features_disabled: string[]
}

export interface MappingAppliedSummary {
  columns_mapped: number
  unmapped_headers: string[]
  value_rules_applied: Record<string, string>
}

export interface QualityReport {
  upload_id: string
  status: "processing" | "ready" | "failed" | "needs_mapping"
  rows_parsed: number | null
  rows_rejected: number | null
  date_range: { start: string | null; end: string | null }
  days_of_history: number | null
  warnings: UploadWarning[]
  mapping_applied: MappingAppliedSummary | null
}

// Data Mapping Layer (Scanwick_Mapping_Layer_Guide.pdf) — the tiered
// column-resolution result POST /upload/csv (when a mapping needs review)
// or POST /mapping/detect returns.
export interface MappingAutoMapped {
  user_header: string
  canonical: string
  tier: "exact" | "fuzzy"
  confidence: number
}

export interface MappingNeedsConfirmation {
  user_header: string
  candidate: string | null
  confidence: number
  prompt: string
}

export interface MappingUnmapped {
  user_header: string
  reason: string
}

export interface MappingValueQuestion {
  field: string
  question: string
  options: string[]
}

export interface MappingDetail {
  auto_mapped: MappingAutoMapped[]
  needs_confirmation: MappingNeedsConfirmation[]
  unmapped: MappingUnmapped[]
  value_questions: MappingValueQuestion[]
}

export interface BankQualityReport {
  transactions_parsed: number | null
  date_range: { start: string | null; end: string | null }
  months_of_data: number | null
  balance_integrity: {
    balance_integrity_passed: boolean | null
    balance_discrepancy: number | null
  } | null
  date_gaps: { start: string; end: string }[]
  warnings: UploadWarning[]
  mapping_applied: MappingAppliedSummary | null
}

interface UploadAcceptedResponse {
  success: boolean
  data: { upload_id: string; status: string; mapping?: MappingDetail }
}

function apiErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.error?.message === "string") {
    return error.response.data.error.message
  }
  return fallback
}

function apiErrorCode(error: unknown): string | null {
  if (isAxiosError(error) && typeof error.response?.data?.error?.code === "string") {
    return error.response.data.error.code
  }
  return null
}

export class UploadApiError extends Error {
  code: string | null
  constructor(message: string, code: string | null = null) {
    super(message)
    this.code = code
  }
}

export async function uploadCsv(params: {
  file: File
  analyzerType: "ecommerce" | "bank"
  merchantId: string
  source: string | null
  bankName?: string | null
  signal?: AbortSignal
}): Promise<{ uploadId: string; status: string; mapping?: MappingDetail }> {
  const form = new FormData()
  form.append("file", params.file)
  form.append("analyzer_type", params.analyzerType)
  form.append("merchant_id", params.merchantId)
  if (params.source) form.append("source", params.source)
  if (params.bankName) form.append("bank_name", params.bankName)

  try {
    const { data } = await apiClient.post<UploadAcceptedResponse>("/upload/csv", form, { signal: params.signal })
    return { uploadId: data.data.upload_id, status: data.data.status, mapping: data.data.mapping }
  } catch (error) {
    if (isAxiosError(error) && error.code === "ERR_CANCELED") throw error
    throw new UploadApiError(apiErrorMessage(error, "Could not upload the file. Please try again."), apiErrorCode(error))
  }
}

// Data Mapping Layer: re-runs column detection against an already-staged
// upload — mainly a "re-check" retry convenience; the primary flow already
// gets this inline from uploadCsv()'s response when a mapping needs review.
export async function detectMapping(uploadId: string, signal?: AbortSignal): Promise<MappingDetail> {
  try {
    const { data } = await apiClient.post<{ data: { upload_id: string; mapping: MappingDetail } }>(
      "/mapping/detect",
      { upload_id: uploadId },
      { signal }
    )
    return data.data.mapping
  } catch (error) {
    if (isAxiosError(error) && error.code === "ERR_CANCELED") throw error
    throw new UploadApiError(apiErrorMessage(error, "Could not re-check the column mapping."))
  }
}

// Persists the user's confirmed/edited mapping and dispatches ingestion —
// mirrors uploadCsv()'s own dispatch-and-poll contract (status: "processing"
// on success, same shape pollQualityReport already expects).
export async function confirmMapping(params: {
  uploadId: string
  mapping: Record<string, string>
  valueRules?: Record<string, string>
  signal?: AbortSignal
}): Promise<{ uploadId: string; status: string }> {
  try {
    const { data } = await apiClient.post<UploadAcceptedResponse>(
      "/mapping/confirm",
      { upload_id: params.uploadId, mapping: params.mapping, value_rules: params.valueRules ?? {} },
      { signal: params.signal }
    )
    return { uploadId: data.data.upload_id, status: data.data.status }
  } catch (error) {
    if (isAxiosError(error) && error.code === "ERR_CANCELED") throw error
    throw new UploadApiError(apiErrorMessage(error, "Could not confirm the column mapping. Please try again."))
  }
}

export async function uploadBankPdf(params: {
  file: File
  merchantId: string
  bankName?: string | null
  password?: string | null
  signal?: AbortSignal
}): Promise<{ uploadId: string }> {
  const form = new FormData()
  form.append("file", params.file)
  form.append("merchant_id", params.merchantId)
  if (params.bankName) form.append("bank_name", params.bankName)
  if (params.password) form.append("password", params.password)

  try {
    const { data } = await apiClient.post<UploadAcceptedResponse>("/bank/upload/pdf", form, { signal: params.signal })
    return { uploadId: data.data.upload_id }
  } catch (error) {
    if (isAxiosError(error) && error.code === "ERR_CANCELED") throw error
    throw new UploadApiError(
      apiErrorMessage(error, "Could not upload the statement. Please try again."),
      apiErrorCode(error),
    )
  }
}

export interface DetectionResult {
  analyzerType: "bank" | "ecommerce" | null
  source: string | null
  confidence: number
  scores: Record<string, number>
}

// Classifies a CSV's likely vertical from its column headers before the
// user has to say whether it's a bank statement, CRM export, or store-
// orders export — the dashboard that opens after upload is driven by this
// result, not by whatever tab happened to be selected beforehand.
export async function detectDatasetType(file: File, signal?: AbortSignal): Promise<DetectionResult> {
  const form = new FormData()
  form.append("file", file)

  try {
    const { data } = await apiClient.post<{
      data: {
        analyzer_type: "bank" | "ecommerce" | null
        source: string | null
        confidence: number
        scores: Record<string, number>
      }
    }>("/upload/detect", form, { signal })
    return {
      analyzerType: data.data.analyzer_type,
      source: data.data.source,
      confidence: data.data.confidence,
      scores: data.data.scores,
    }
  } catch (error) {
    if (isAxiosError(error) && error.code === "ERR_CANCELED") throw error
    throw new UploadApiError(apiErrorMessage(error, "Could not analyze this file."))
  }
}

export interface MonoIngestResult {
  account_id: string
  transactions_created: number
  rows_rejected: number
}

// Synchronous, not staged/polled — Mono is a live API call, not a file, and
// the backend returns the full result directly (see docs/INTEGRATION_PLAN.md
// Phase 3: no durable Upload row exists for this path yet).
export async function uploadMono(params: {
  merchantId: string
  monoAccountId: string
}): Promise<MonoIngestResult> {
  try {
    const { data } = await apiClient.post<{ data: MonoIngestResult }>("/bank/upload/mono", {
      merchant_id: params.merchantId,
      mono_account_id: params.monoAccountId,
    })
    return data.data
  } catch (error) {
    throw new UploadApiError(apiErrorMessage(error, "Could not connect this account. Please try again."))
  }
}

export async function getQualityReport(uploadId: string, signal?: AbortSignal): Promise<QualityReport> {
  const { data } = await apiClient.get<{ data: QualityReport }>(`/upload/${uploadId}/quality-report`, { signal })
  return data.data
}

export async function getBankQualityReport(uploadId: string, signal?: AbortSignal): Promise<BankQualityReport> {
  const { data } = await apiClient.get<{ data: BankQualityReport }>(`/bank/upload/${uploadId}/quality-report`, { signal })
  return data.data
}

// Bank uploads (PDF/CSV) run through a Celery task and don't have a status
// field on their own quality-report shape — status is only exposed on the
// generic ecommerce one. For bank we treat "found with rows_parsed
// populated" as ready, and just keep polling on 404 (not created yet).
//
// `options.signal` lets a caller cancel an in-flight poll (reset, tab
// switch, unmount) — any pending HTTP request is aborted immediately via
// axios, and the loop itself is checked for cancellation right after each
// request and after each wait interval so a stale poll never lingers past
// the point the caller stopped caring about it.
export async function pollQualityReport(
  uploadId: string,
  isBank: boolean,
  options: { intervalMs?: number; timeoutMs?: number; signal?: AbortSignal } = {}
): Promise<QualityReport | BankQualityReport> {
  const intervalMs = options.intervalMs ?? 2000
  const timeoutMs = options.timeoutMs ?? 120_000
  const deadline = Date.now() + timeoutMs
  const { signal } = options

  while (Date.now() < deadline) {
    if (signal?.aborted) throw new UploadApiError("Upload cancelled.")

    try {
      if (isBank) {
        const report = await getBankQualityReport(uploadId, signal)
        if (report.transactions_parsed !== null) return report
      } else {
        const report = await getQualityReport(uploadId, signal)
        if (report.status !== "processing") return report
      }
    } catch (error) {
      if (isAxiosError(error) && error.code === "ERR_CANCELED") throw error
      if (!isAxiosError(error) || error.response?.status !== 404) throw error
      // 404 while the Celery task hasn't created the Upload... row update
      // yet isn't expected (the route creates it up front) — but keep
      // polling rather than failing hard on a transient race.
    }

    if (signal?.aborted) throw new UploadApiError("Upload cancelled.")
    await new Promise((resolve) => window.setTimeout(resolve, intervalMs))
    if (signal?.aborted) throw new UploadApiError("Upload cancelled.")
  }

  throw new UploadApiError("Processing is taking longer than expected. Check back shortly.")
}

export interface NormalizedCheck {
  label: string
  status: "pass" | "fail" | "warning"
  badgeLabel?: string
}

export interface NormalizedWarning {
  severity: "critical" | "warning"
  field: string
  description: string
  fix: string
}

export interface NormalizedDisabledFeature {
  name: string
  description: string
}

export interface NormalizedQualityData {
  state: "clean" | "warning" | "failed"
  rowsParsed: number | null
  rowsRejected: number | null
  dateRangeLabel: string
  warnings: NormalizedWarning[]
  checks: NormalizedCheck[]
  disabledFeatures: NormalizedDisabledFeature[]
  mappingApplied: MappingAppliedSummary | null
}

function formatDateRange(range: { start: string | null; end: string | null }, daysOfHistory: number | null): string {
  if (!range.start || !range.end) return "—"
  const format = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" })
  const label = `${format(range.start)} – ${format(range.end)}`
  return daysOfHistory ? `${label} · ${daysOfHistory} days` : label
}

// Real elapsed-day count between a date range's start/end, inclusive of both
// endpoints (e.g. Jan 30 - Feb 3 => 5 days). Used instead of approximating
// from `months_of_data`, which counts distinct calendar months touched, not
// elapsed time, and can badly overstate a short range that crosses a month
// boundary (that same Jan 30 - Feb 3 range touches 2 calendar months).
function daysOfHistoryFromRange(range: { start: string | null; end: string | null }): number | null {
  if (!range.start || !range.end) return null
  const startDate = new Date(range.start)
  const endDate = new Date(range.end)
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return null
  const diffMs = endDate.getTime() - startDate.getTime()
  return Math.round(diffMs / (1000 * 60 * 60 * 24)) + 1
}

function mapWarnings(warnings: UploadWarning[]): NormalizedWarning[] {
  return warnings.map((warning) => ({
    severity: warning.severity === "high" ? "critical" : "warning",
    field: warning.field,
    description: warning.message,
    fix: warning.features_disabled.length
      ? `Disables: ${warning.features_disabled.join(", ")}.`
      : "Review this upload before proceeding.",
  }))
}

function mapDisabledFeatures(warnings: UploadWarning[]): NormalizedDisabledFeature[] {
  const byName = new Map<string, string>()
  for (const warning of warnings) {
    for (const name of warning.features_disabled) {
      if (!byName.has(name)) byName.set(name, warning.message)
    }
  }
  return Array.from(byName, ([name, description]) => ({ name, description }))
}

export function normalizeQualityReport(
  report: QualityReport | BankQualityReport,
  isBank: boolean
): NormalizedQualityData {
  if (isBank) {
    const bank = report as BankQualityReport
    const balancePassed = bank.balance_integrity?.balance_integrity_passed ?? null
    const gapCount = bank.date_gaps.length
    const failed = balancePassed === false
    const warning = !failed && (gapCount > 0 || bank.warnings.length > 0)

    return {
      state: failed ? "failed" : warning ? "warning" : "clean",
      rowsParsed: bank.transactions_parsed,
      rowsRejected: null,
      dateRangeLabel: formatDateRange(bank.date_range, daysOfHistoryFromRange(bank.date_range)),
      warnings: mapWarnings(bank.warnings),
      disabledFeatures: mapDisabledFeatures(bank.warnings),
      mappingApplied: bank.mapping_applied,
      checks: [
        {
          label: "Balance integrity",
          status: balancePassed === false ? "fail" : balancePassed === true ? "pass" : "warning",
        },
        {
          label: "Date continuity",
          status: gapCount > 0 ? "warning" : "pass",
          badgeLabel: gapCount > 0 ? `${gapCount} gap${gapCount === 1 ? "" : "s"}` : undefined,
        },
        { label: "Months of data", status: (bank.months_of_data ?? 0) >= 3 ? "pass" : "warning" },
      ],
    }
  }

  const generic = report as QualityReport
  const rowsRejected = generic.rows_rejected ?? 0
  const failed = generic.status === "failed"
  const warning = !failed && (rowsRejected > 0 || generic.warnings.length > 0)

  return {
    state: failed ? "failed" : warning ? "warning" : "clean",
    rowsParsed: generic.rows_parsed,
    rowsRejected: generic.rows_rejected,
    dateRangeLabel: formatDateRange(generic.date_range, generic.days_of_history),
    warnings: mapWarnings(generic.warnings),
    disabledFeatures: mapDisabledFeatures(generic.warnings),
    mappingApplied: generic.mapping_applied,
    checks: [
      { label: "Rows parsed", status: failed ? "fail" : "pass" },
      {
        label: "Rejected rows",
        status: rowsRejected > 0 ? "warning" : "pass",
        badgeLabel: rowsRejected > 0 ? `${rowsRejected} rejected` : undefined,
      },
      { label: "Data-quality warnings", status: generic.warnings.length > 0 ? "warning" : "pass" },
    ],
  }
}
