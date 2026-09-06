/** Shared domain types mirroring the FastAPI backend responses. */

export interface HealthResponse {
  status: string
}

export interface MetricRow {
  id: number
  company: string
  year: string
  revenue: string | null
  net_income: string | null
  operating_income: string | null
  cash_flow: string | null
  total_assets: string | null
  total_liabilities: string | null
  risk_factors: string | null
  growth_drivers: string | null
  executive_summary: string | null
  created_at: string | null
}

export interface MetricsResponse {
  count: number
  metrics: MetricRow[]
}

export interface ChatPayload {
  question: string
  company?: string | null
  year?: number | null
}

export interface ChatResponse {
  answer: string
}

export interface UploadResponse {
  message: string
  filename: string
  chunks_indexed: number
}