import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  ArrowDownRight,
  ArrowUpRight,
  Banknote,
  FileStack,
  Gauge,
  RefreshCw,
  Scale,
  Wallet,
} from 'lucide-react'

import { Pill, SectionTitle } from '../components/ui'
import { api } from '../lib/api'
import {
  formatCompactBn,
  initials,
  parseMoney,
  shortName,
} from '../lib/format'
import type { MetricRow } from '../types'

const CHART_COLORS = {
  revenue: '#34d399',
  netIncome: '#38bdf8',
  operatingIncome: '#a78bfa',
  cashFlow: '#fbbf24',
  assets: '#34d399',
  liabilities: '#fb7185',
}

interface ChartDatum {
  name: string
  revenue: number | null
  netIncome: number | null
  operatingIncome: number | null
  cashFlow: number | null
  assets: number | null
  liabilities: number | null
}

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

const tooltipStyle = {
  backgroundColor: '#0d1526',
  border: '1px solid rgba(148,163,184,0.2)',
  borderRadius: '0.75rem',
  fontSize: 12,
}

function toolValue(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string') {
    const n = Number(value)
    return Number.isNaN(n) ? null : n
  }
  return null
}

export default function FinancialComparison() {
  const { data, loading, error, refresh } = useMetrics()

  const companies = useMemo(
    () => Array.from(new Set(data.map((row) => row.company))),
    [data],
  )

  const chartData = useMemo<ChartDatum[]>(
    () =>
      companies.map((company) => {
        const row = data
          .filter((r) => r.company === company)
          .sort((a, b) => b.year.localeCompare(a.year))[0]
        if (!row) return null as unknown as ChartDatum
        return {
          name: shortName(company),
          revenue: parseMoney(row.revenue),
          netIncome: parseMoney(row.net_income),
          operatingIncome: parseMoney(row.operating_income),
          cashFlow: parseMoney(row.cash_flow),
          assets: parseMoney(row.total_assets),
          liabilities: parseMoney(row.total_liabilities),
        }
      }),
    [companies, data],
  )

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
          Could not load financial comparison
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
          platform will extract financial metrics for comparison.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-brand-400">
            Investor Intelligence
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">
            Financial <span className="text-gradient">Comparison</span>
          </h1>
          <p className="mt-1.5 max-w-2xl text-sm text-slate-400">
            Compare key financial metrics across all ingested companies side by
            side.
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Pill tone="emerald">
            {companies.length} {companies.length === 1 ? 'company' : 'companies'}
          </Pill>
          <Pill tone="sky">{data.length} reports</Pill>
        </div>
      </header>

      {/* Charts */}
      <section className="grid gap-6 md:grid-cols-2">
        <ChartPanel
          title="Revenue vs Net Income"
          subtitle="Latest fiscal year · in USD billions"
        >
          <ComparableBarChart
            data={chartData}
            bars={[
              { key: 'revenue', name: 'Revenue', color: CHART_COLORS.revenue },
              {
                key: 'netIncome',
                name: 'Net Income',
                color: CHART_COLORS.netIncome,
              },
            ]}
          />
        </ChartPanel>

        <ChartPanel
          title="Operating Income vs Cash Flow"
          subtitle="Latest fiscal year · in USD billions"
        >
          <ComparableBarChart
            data={chartData}
            bars={[
              {
                key: 'operatingIncome',
                name: 'Operating Income',
                color: CHART_COLORS.operatingIncome,
              },
              {
                key: 'cashFlow',
                name: 'Cash Flow',
                color: CHART_COLORS.cashFlow,
              },
            ]}
          />
        </ChartPanel>
      </section>

      <section>
        <ChartPanel
          full
          title="Balance sheet: Total Assets vs Total Liabilities"
          subtitle="Latest fiscal year · in USD billions"
        >
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} barGap={4} margin={{ left: -8, right: 8 }}>
              <defs>
                <linearGradient id="gradAssets" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={CHART_COLORS.assets} stopOpacity={0.95} />
                  <stop offset="100%" stopColor={CHART_COLORS.assets} stopOpacity={0.35} />
                </linearGradient>
                <linearGradient id="gradLiab" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={CHART_COLORS.liabilities} stopOpacity={0.9} />
                  <stop offset="100%" stopColor={CHART_COLORS.liabilities} stopOpacity={0.3} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(148,163,184,0.08)" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: 'rgba(148,163,184,0.15)' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#64748b', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => formatCompactBn(v)}
              />
              <Tooltip
                cursor={{ fill: 'rgba(148,163,184,0.06)' }}
                contentStyle={tooltipStyle}
                formatter={(value, name) => [
                  formatCompactBn(toolValue(value)),
                  String(name),
                ]}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, color: '#94a3b8' }}
                iconType="circle"
              />
              <Bar dataKey="assets" name="Assets" fill="url(#gradAssets)" radius={[6, 6, 0, 0]} maxBarSize={42} />
              <Bar dataKey="liabilities" name="Liabilities" fill="url(#gradLiab)" radius={[6, 6, 0, 0]} maxBarSize={42} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>
      </section>

      {/* KPI comparison */}
      <KpiComparisonGrid rows={companyRows} />
    </div>
  )
}

function ChartPanel({
  title,
  subtitle,
  children,
  full = false,
}: {
  title: string
  subtitle: string
  children: ReactNode
  full?: boolean
}) {
  return (
    <div className={`panel p-5 ${full ? '' : 'h-full min-h-[340px]'}`}>
      <SectionTitle title={title} subtitle={subtitle} />
      <div className="h-[260px]">{children}</div>
    </div>
  )
}

function ComparableBarChart({
  data,
  bars,
}: {
  data: ChartDatum[]
  bars: { key: keyof ChartDatum; name: string; color: string }[]
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} barGap={4} margin={{ left: -8, right: 8 }}>
        <defs>
          {bars.map((bar) => (
            <linearGradient
              key={String(bar.key)}
              id={`grad-${String(bar.key)}`}
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" stopColor={bar.color} stopOpacity={0.95} />
              <stop offset="100%" stopColor={bar.color} stopOpacity={0.3} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid stroke="rgba(148,163,184,0.08)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          axisLine={{ stroke: 'rgba(148,163,184,0.15)' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#64748b', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => formatCompactBn(v)}
        />
        <Tooltip
          cursor={{ fill: 'rgba(148,163,184,0.06)' }}
          contentStyle={tooltipStyle}
          formatter={(value, name) => [
            formatCompactBn(toolValue(value)),
            String(name),
          ]}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} iconType="circle" />
        {bars.map((bar) => (
          <Bar
            key={String(bar.key)}
            dataKey={String(bar.key)}
            name={bar.name}
            fill={`url(#grad-${String(bar.key)})`}
            radius={[6, 6, 0, 0]}
            maxBarSize={42}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
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
