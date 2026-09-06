import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  ArrowDownRight,
  ArrowUpRight,
  Banknote,
  Building2,
  FileStack,
  Gauge,
  RefreshCw,
  Scale,
  TrendingUp,
  TriangleAlert,
  Wallet,
} from 'lucide-react'

import { Pill, SectionTitle } from '../components/ui'
import { api } from '../lib/api'
import { initials, parseMoney, parseStringList } from '../lib/format'
import type { MetricRow } from '../types'

function useMetrics() {
  const [data, setData] = useState<MetricRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api
      .metrics()
      .then((res) => {
        setData(res.metrics)
        setError(null)
        setLoading(false)
      })
      .catch((err: Error) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  const refresh = useCallback(() => {
    setError(null)
    setLoading(true)
    load()
  }, [load])

  useEffect(() => {
    load()
  }, [load])

  return { data, loading, error, refresh }
}

export default function Dashboard() {
  const { data, loading, error, refresh } = useMetrics()
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null)

  const companies = useMemo(
    () => Array.from(new Set(data.map((row) => row.company))),
    [data],
  )

  const selected = selectedCompany ?? companies[0] ?? null

  const selectedRows = useMemo(
    () =>
      data
        .filter((row) => row.company === selected)
        .sort((a, b) => b.year.localeCompare(a.year)),
    [data, selected],
  )
  const selectedRow = selectedRows[0]

  const companyRows = useMemo(
    () =>
      companies
        .map((company) => {
          const row = data
            .filter((r) => r.company === company)
            .sort((a, b) => b.year.localeCompare(a.year))[0]
          return row ?? null
        })
        .filter((r): r is MetricRow => r !== null),
    [companies, data],
  )

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-slate-400">
          <RefreshCw size={28} className="animate-spin text-brand-400" />
          <p className="text-sm">Loading financial metrics…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="panel flex flex-col items-start gap-3 border-rose-500/30 p-8">
        <h2 className="text-lg font-semibold text-rose-300">
          Could not load dashboard
        </h2>
        <p className="text-sm text-slate-400">{error}</p>
        <button
          type="button"
          onClick={refresh}
          className="rounded-lg bg-brand-500/10 px-4 py-2 text-sm font-medium text-brand-300 ring-1 ring-brand-500/30 transition hover:bg-brand-500/20"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!data.length) {
    return (
      <div className="panel flex flex-col items-center gap-4 p-12 text-center">
        <FileStack size={36} className="text-brand-400/70" />
        <h2 className="text-xl font-semibold text-slate-100">
          No financial metrics yet
        </h2>
        <p className="max-w-md text-sm leading-relaxed text-slate-400">
          Ingest an annual report (e.g. <code>2024_Apple.pdf</code>) and the
          platform will extract financial metrics and surface them here.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-8">
      <PageHeader count={data.length} companyCount={companies.length} />

      <SummaryCards
        companyCount={companies.length}
        reportCount={data.length}
      />

      {/* KPI comparison */}
      <KpiComparisonGrid rows={companyRows} />

      {/* Detailed company analysis */}
      <CompanyDetailedSection
        options={companyRows}
        selected={selected}
        selectedRow={selectedRow}
        onSelect={(company) => setSelectedCompany(company)}
      />
    </div>
  )
}

function PageHeader({
  count,
  companyCount,
}: {
  count: number
  companyCount: number
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-brand-400">
          Investor Intelligence
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">
          Financial <span className="text-gradient">Overview</span>
        </h1>
        <p className="mt-1.5 max-w-2xl text-sm text-slate-400">
          Extracted KPIs from ingested annual reports, sourced from your
          PostgreSQL metrics store.
        </p>
      </div>
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <Pill tone="emerald">
          {companyCount} {companyCount === 1 ? 'company' : 'companies'}
        </Pill>
        <Pill tone="sky">{count} reports</Pill>
      </div>
    </header>
  )
}

function SummaryCards({
  companyCount,
  reportCount,
}: {
  companyCount: number
  reportCount: number
}) {
  const cards = [
    { label: 'Companies tracked', value: String(companyCount), icon: Building2, tone: 'text-brand-300 bg-brand-500/10' },
    { label: 'Reports analyzed', value: String(reportCount), icon: FileStack, tone: 'text-accent-400 bg-accent-500/10' },
  ]
  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <div
            key={card.label}
            className="panel panel-hover flex items-center gap-4 p-5"
          >
            <div
              className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${card.tone}`}
            >
              <Icon size={22} />
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                {card.label}
              </p>
              <p className="text-2xl font-bold tracking-tight text-slate-100">
                {card.value}
              </p>
            </div>
          </div>
        )
      })}
    </section>
  )
}

const FIGURE_RE = /\$[\d,.]+[BM]?|\d[\d,]*(?:\.\d+)?%/

function renderHighlightedFigures(text: string): ReactNode {
  const parts = text.split(/(\$[\d,.]+[BM]?|\d[\d,]*(?:\.\d+)?%)/g)
  return parts.map((part, index) =>
    FIGURE_RE.test(part) ? (
      <strong key={index} className="font-semibold text-brand-300">
        {part}
      </strong>
    ) : (
      <span key={index}>{part}</span>
    ),
  )
}

function CompanyDetailedSection({
  options,
  selected,
  selectedRow,
  onSelect,
}: {
  options: MetricRow[]
  selected: string | null
  selectedRow: MetricRow | undefined
  onSelect: (company: string) => void
}) {
  const riskFactors = selectedRow
    ? parseStringList(selectedRow.risk_factors)
    : []
  const growthDrivers = selectedRow
    ? parseStringList(selectedRow.growth_drivers)
    : []
  const executiveSummary = selectedRow
    ? parseStringList(selectedRow.executive_summary)
    : []

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-brand-400">
            Detailed analysis
          </p>
          <h2 className="text-lg font-semibold tracking-tight text-slate-100">
            Company Breakdown
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Select a company to review its risk factors, growth drivers, and
            executive summary.
          </p>
        </div>
        <select
          value={selected ?? ''}
          onChange={(e) => onSelect(e.target.value)}
          aria-label="Select company for detailed analysis"
          className="w-56 rounded-lg border border-slate-600/70 bg-ink-700/70 px-3 py-2 text-sm text-slate-100 focus:border-brand-500/60 focus:outline-none sm:w-60 [color-scheme:dark]"
        >
          {options.map((row) => (
            <option
              key={row.company}
              value={row.company}
              className="bg-ink-900 text-slate-100"
            >
              {row.company} FY{row.year}
            </option>
          ))}
        </select>
      </div>

      {selectedRow && (
        <div className="flex flex-col gap-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="panel flex flex-col gap-3 p-5">
              <SectionTitle
                title="Risk Factors"
                subtitle="Top risks extracted from the annual report"
              />
              {riskFactors.length ? (
                <ul className="flex flex-col gap-2">
                  {riskFactors.map((item, index) => (
                    <li
                      key={index}
                      className="flex gap-2.5 rounded-lg border border-rose-500/10 bg-rose-500/5 px-3.5 py-2.5 text-sm leading-relaxed text-slate-300"
                    >
                      <TriangleAlert
                        size={14}
                        className="mt-0.5 shrink-0 text-rose-400"
                      />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500">
                  No risk factors extracted.
                </p>
              )}
            </div>

            <div className="panel flex flex-col gap-3 p-5">
              <SectionTitle
                title="Growth Drivers"
                subtitle="Momentum drivers extracted from the annual report"
              />
              {growthDrivers.length ? (
                <ul className="flex flex-col gap-2">
                  {growthDrivers.map((item, index) => (
                    <li
                      key={index}
                      className="flex gap-2.5 rounded-lg border border-brand-500/10 bg-brand-500/5 px-3.5 py-2.5 text-sm leading-relaxed text-slate-300"
                    >
                      <TrendingUp
                        size={14}
                        className="mt-0.5 shrink-0 text-brand-400"
                      />
                      <span>{renderHighlightedFigures(item)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500">
                  No growth drivers extracted.
                </p>
              )}
            </div>
          </div>

          <div className="panel flex flex-col gap-3 p-6">
            <SectionTitle
              title="Executive Financial Summary"
              subtitle="Extracted narrative highlights from the report"
            />
            {executiveSummary.length ? (
              <ul className="flex flex-col gap-2.5">
                {executiveSummary.map((point, index) => (
                  <li
                    key={index}
                    className="flex gap-2.5 text-sm leading-relaxed text-slate-300"
                  >
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">
                No executive summary extracted.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

type KpiKey =
  | 'revenue'
  | 'netIncome'
  | 'operatingIncome'
  | 'cashFlow'
  | 'assets'
  | 'liabilities'

const KPI_DEFS = [
  { key: 'revenue', title: 'Revenue', subtitle: 'Total company revenue', icon: Banknote, tone: 'text-brand-300 bg-brand-500/10' },
  { key: 'netIncome', title: 'Net Income', subtitle: 'Net profitability after expenses', icon: ArrowUpRight, tone: 'text-sky-300 bg-sky-500/10' },
  { key: 'operatingIncome', title: 'Operating Income', subtitle: 'Income from core operations', icon: Gauge, tone: 'text-violet-300 bg-violet-500/10' },
  { key: 'cashFlow', title: 'Operating Cash Flow', subtitle: 'Cash generated from operations', icon: Wallet, tone: 'text-amber-300 bg-amber-500/10' },
  { key: 'assets', title: 'Total Assets', subtitle: 'Everything the company owns', icon: Scale, tone: 'text-emerald-300 bg-emerald-500/10' },
  { key: 'liabilities', title: 'Total Liabilities', subtitle: 'Outstanding financial obligations', icon: ArrowDownRight, tone: 'text-rose-300 bg-rose-500/10' },
] as const

const COMPANY_BAR_COLORS = ['#34d399', '#38bdf8', '#a78bfa', '#fbbf24', '#f472b6', '#fb7185']

const COMPANY_CHIP_CLASSES = [
  'bg-brand-500/15 text-brand-300',
  'bg-accent-500/15 text-accent-400',
  'bg-violet-500/15 text-violet-300',
  'bg-amber-500/15 text-amber-300',
  'bg-pink-500/15 text-pink-300',
  'bg-rose-500/15 text-rose-300',
]

function kpiValue(row: MetricRow, key: KpiKey): string | null {
  switch (key) {
    case 'revenue':
      return row.revenue
    case 'netIncome':
      return row.net_income
    case 'operatingIncome':
      return row.operating_income
    case 'cashFlow':
      return row.cash_flow
    case 'assets':
      return row.total_assets
    case 'liabilities':
      return row.total_liabilities
  }
}

function KpiComparisonGrid({ rows }: { rows: MetricRow[] }) {
  return (
    <section className="flex flex-col gap-6">
      <SectionTitle
        title="KPI Comparison"
        subtitle="Compare the same metric across every ingested company's latest fiscal year"
      />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {KPI_DEFS.map((def) => (
          <KpiCompareCard key={def.key} def={def} rows={rows} />
        ))}
      </div>
    </section>
  )
}

function KpiCompareCard({
  def,
  rows,
}: {
  def: (typeof KPI_DEFS)[number]
  rows: MetricRow[]
}) {
  const Icon = def.icon
  const values = rows.map((row) => parseMoney(kpiValue(row, def.key)))
  const finite = values.filter(
    (v): v is number => typeof v === 'number' && Number.isFinite(v),
  )
  const max = finite.length ? Math.max(...finite) : 0

  return (
    <div className="panel panel-hover flex flex-col gap-2.5 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            {def.title}
          </p>
          <p className="mt-0.5 truncate text-[11px] text-slate-500">
            {def.subtitle}
          </p>
        </div>
        <div
          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${def.tone}`}
        >
          <Icon size={14} />
        </div>
      </div>

      <div className="flex flex-col gap-2.5">
        {rows.map((row, index) => {
          const raw = kpiValue(row, def.key)
          const numeric = parseMoney(raw)
          const pct =
            numeric !== null && max > 0 && numeric >= 0
              ? Math.min(100, Math.max(4, (numeric / max) * 100))
              : 0
          const accentIndex = index % COMPANY_BAR_COLORS.length
          return (
            <div
              key={`${row.company}-${row.year}`}
              className="flex flex-col gap-1"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[10px] font-bold ${COMPANY_CHIP_CLASSES[accentIndex]}`}
                >
                  {initials(row.company)}
                </span>
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-200">
                  {row.company}{' '}
                  <span className="text-slate-500">({row.year})</span>
                </span>
                <span className="shrink-0 text-sm font-semibold tabular-nums text-slate-100">
                  {raw ?? '—'}
                </span>
              </div>
              <div className="ml-8 h-1 overflow-hidden rounded-full bg-ink-700/60">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${pct}%`,
                    background: `linear-gradient(90deg, ${COMPANY_BAR_COLORS[accentIndex]} 0%, ${COMPANY_BAR_COLORS[accentIndex]}55 60%, ${COMPANY_BAR_COLORS[accentIndex]}14 100%)`,
                    boxShadow: `0 0 6px ${COMPANY_BAR_COLORS[accentIndex]}40`,
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
