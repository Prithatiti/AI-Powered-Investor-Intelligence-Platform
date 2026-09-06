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
  Building2,
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
  parseStringList,
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
  fontSize: 13,
}

/** Coerce a recharts tooltip value into a plain number (or null). */
function toolValue(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string') {
    const n = Number(value)
    return Number.isNaN(n) ? null : n
  }
  return null
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

  const summary = useMemo(() => {
    const values = chartData.filter(
      (d): d is ChartDatum & { revenue: number; netIncome: number } =>
        d !== null,
    )
    const avgRevenue =
      values.reduce((sum, d) => sum + (d.revenue ?? 0), 0) /
      Math.max(values.length, 1)
    const avgNetIncome =
      values.reduce((sum, d) => sum + (d.netIncome ?? 0), 0) /
      Math.max(values.length, 1)
    return { avgRevenue, avgNetIncome }
  }, [chartData])

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
        avgRevenue={summary.avgRevenue}
        avgNetIncome={summary.avgNetIncome}
        companyCount={companies.length}
        reportCount={data.length}
      />

      {/* Company selector */}
      <section>
        <SectionTitle
          title="Reports analyzed"
          subtitle="Select a company to drill into its scorecard"
        />
        <div className="flex flex-wrap gap-2.5">
          {companies.map((company) => {
            const active = company === selected
            return (
              <button
                key={company}
                type="button"
                onClick={() => setSelectedCompany(company)}
                className={`flex items-center gap-2.5 rounded-xl border px-3.5 py-2 transition-all ${
                  active
                    ? 'border-brand-500/50 bg-brand-500/10 text-brand-200 shadow-glow'
                    : 'border-slate-700/60 bg-ink-800/40 text-slate-300 hover:border-slate-600 hover:text-slate-100'
                }`}
              >
                <span
                  className={`flex h-7 w-7 items-center justify-center rounded-lg text-[11px] font-bold ${
                    active
                      ? 'bg-brand-500 text-ink-950'
                      : 'bg-ink-700 text-slate-300'
                  }`}
                >
                  {initials(company)}
                </span>
                <span className="text-sm font-medium">{company}</span>
                <span className="text-xs text-slate-500">
                  FY{selectedRows[0]?.year}
                </span>
              </button>
            )
          })}
        </div>
      </section>

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
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(148,163,184,0.15)' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#64748b', fontSize: 12 }}
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
                wrapperStyle={{ fontSize: 12, color: '#94a3b8' }}
                iconType="circle"
              />
              <Bar dataKey="assets" name="Assets" fill="url(#gradAssets)" radius={[6, 6, 0, 0]} maxBarSize={42} />
              <Bar dataKey="liabilities" name="Liabilities" fill="url(#gradLiab)" radius={[6, 6, 0, 0]} maxBarSize={42} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>
      </section>

      {/* Company scorecard */}
      {selectedRow && <CompanyScorecard row={selectedRow} />}
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
  avgRevenue,
  avgNetIncome,
  companyCount,
  reportCount,
}: {
  avgRevenue: number
  avgNetIncome: number
  companyCount: number
  reportCount: number
}) {
  const cards = [
    { label: 'Companies tracked', value: String(companyCount), icon: Building2, tone: 'text-brand-300 bg-brand-500/10' },
    { label: 'Reports analyzed', value: String(reportCount), icon: FileStack, tone: 'text-accent-400 bg-accent-500/10' },
    { label: 'Avg revenue', value: formatCompactBn(avgRevenue), icon: Banknote, tone: 'text-violet-300 bg-violet-500/10' },
    { label: 'Avg net income', value: formatCompactBn(avgNetIncome), icon: Gauge, tone: 'text-amber-300 bg-amber-500/10' },
  ]
  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
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
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          axisLine={{ stroke: 'rgba(148,163,184,0.15)' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#64748b', fontSize: 12 }}
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
        <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} iconType="circle" />
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

function CompanyScorecard({ row }: { row: MetricRow }) {
  const riskFactors = parseStringList(row.risk_factors)
  const growthDrivers = parseStringList(row.growth_drivers)
  const executiveSummary = parseStringList(row.executive_summary)

  const metrics = [
    { label: 'Revenue', value: row.revenue, key: 'revenue' as const, icon: Banknote, tone: 'text-brand-300 bg-brand-500/10' },
    { label: 'Net Income', value: row.net_income, key: 'netIncome' as const, icon: ArrowUpRight, tone: 'text-sky-300 bg-sky-500/10' },
    { label: 'Operating Income', value: row.operating_income, key: 'operatingIncome' as const, icon: Gauge, tone: 'text-violet-300 bg-violet-500/10' },
    { label: 'Cash Flow', value: row.cash_flow, key: 'cashFlow' as const, icon: Wallet, tone: 'text-amber-300 bg-amber-500/10' },
    { label: 'Total Assets', value: row.total_assets, key: 'assets' as const, icon: Scale, tone: 'text-emerald-300 bg-emerald-500/10' },
    { label: 'Total Liabilities', value: row.total_liabilities, key: 'liabilities' as const, icon: ArrowDownRight, tone: 'text-rose-300 bg-rose-500/10' },
  ]

  return (
    <section className="flex flex-col gap-6">
      <SectionTitle
        title={`${row.company} · FY${row.year} scorecard`}
        subtitle="Financial KPIs extracted from the annual report"
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {metrics.map((metric) => {
          const Icon = metric.icon
          const numeric = parseMoney(valueFor(row, metric.key))
          return (
            <div key={metric.label} className="panel panel-hover p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                  {metric.label}
                </p>
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-lg ${metric.tone}`}
                >
                  <Icon size={16} />
                </div>
              </div>
              <p className="mt-2 text-2xl font-bold tracking-tight text-slate-100">
                {metric.value ?? '—'}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {numeric !== null ? `${formatCompactBn(numeric)} USD` : 'Not disclosed'}
              </p>
            </div>
          )
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ListPanel
          title="Top risk factors"
          items={riskFactors}
          tone="rose"
          empty="No risk factors extracted."
        />
        <ListPanel
          title="Top growth drivers"
          items={growthDrivers}
          tone="emerald"
          empty="No growth drivers extracted."
        />
      </div>

      <div className="panel p-6">
        <SectionTitle
          title="Executive-level financial summary"
          subtitle="Extracted narrative highlights from the report"
        />
        {executiveSummary.length ? (
          <ul className="flex flex-col gap-3">
            {executiveSummary.map((point, index) => (
              <li key={index} className="flex gap-3 text-sm leading-relaxed text-slate-300">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" />
                <span>{point}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">No executive summary extracted.</p>
        )}
      </div>
    </section>
  )
}

function valueFor(row: MetricRow, key: 'revenue' | 'netIncome' | 'operatingIncome' | 'cashFlow' | 'assets' | 'liabilities'): string | null {
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

function ListPanel({
  title,
  items,
  tone,
  empty,
}: {
  title: string
  items: string[]
  tone: 'rose' | 'emerald'
  empty: string
}) {
  const dot = tone === 'rose' ? 'bg-rose-400' : 'bg-brand-400'
  return (
    <div className="panel p-6">
      <SectionTitle title={title} />
      {items.length ? (
        <ul className="flex flex-col gap-3">
          {items.map((item, index) => (
            <li
              key={index}
              className="flex gap-3 rounded-lg border border-slate-800/50 bg-ink-800/30 px-3.5 py-2.5 text-sm leading-relaxed text-slate-300"
            >
              <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">{empty}</p>
      )}
    </div>
  )
}