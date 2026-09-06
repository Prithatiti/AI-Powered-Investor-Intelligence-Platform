import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  MessagesSquare,
  Rocket,
  Search,
  Sparkles,
  TrendingUp,
  UploadCloud,
  Wand2,
} from 'lucide-react'

const FEATURES = [
  {
    title: 'Report Ingestion',
    description:
      'Upload annual reports as PDF, Markdown, or text. Reports are automatically converted, semantically chunked, and embedded into Azure AI Search.',
    icon: UploadCloud,
    cta: { label: 'Ingest a report', to: '/ingestion' },
    points: ['Drag & drop upload', 'Filename-aware parsing', 'Chunked for retrieval'],
  },
  {
    title: 'Financial Intelligence',
    description:
      'Key metrics are auto-extracted per report: revenue, net income, cash flow, balance sheet, risks, and growth drivers.',
    icon: BarChart3,
    cta: { label: 'Open dashboard', to: '/dashboard' },
    points: ['KPI extraction pipeline', 'Company scorecards', 'Charts & comparisons'],
  },
  {
    title: 'AI Research Analyst',
    description:
      'Ask natural-language questions about any ingested report and get grounded answers generated from the indexed evidence.',
    icon: MessagesSquare,
    cta: { label: 'Start a chat', to: '/research' },
    points: ['Grounded answers', 'Company scoped or cross-company', 'Source-backed context'],
  },
]

const STEPS = [
  {
    step: '01',
    title: 'Upload your report',
    text: 'Drop in an annual report named like 2024_Apple.pdf.',
    icon: UploadCloud,
  },
  {
    step: '02',
    title: 'AI extracts the insights',
    text: 'Chunks are indexed and KPIs, risks, and growth drivers extracted.',
    icon: Wand2,
  },
  {
    step: '03',
    title: 'Explore & ask anything',
    text: 'Visualize scorecards or chat with the AI research analyst.',
    icon: Search,
  },
]

export default function Home() {
  return (
    <div className="flex flex-col gap-10">
      {/* Hero */}
      <section className="panel relative overflow-hidden p-8 sm:p-12">
        <div className="pointer-events-none absolute -right-28 -top-28 h-80 w-80 rounded-full bg-brand-500/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-28 -left-20 h-80 w-80 rounded-full bg-accent-500/10 blur-3xl" />

        <div className="relative">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500 shadow-glow">
                <TrendingUp size={23} className="text-ink-950" strokeWidth={2.5} />
              </div>
              <div className="leading-tight">
                <p className="text-xl font-bold tracking-tight text-slate-50">
                  InvestorIQ <span className="text-gradient">AI</span>
                </p>
                <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500">
                  Investor Intelligence
                </p>
              </div>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-500/30 bg-brand-500/10 px-3 py-1 text-xs font-medium text-brand-300">
              <Sparkles size={13} /> AI-powered investor intelligence
            </span>
          </div>

          <h1 className="mt-6 max-w-3xl text-4xl font-bold leading-tight tracking-tight text-slate-50 sm:text-5xl">
            Turn annual reports into{' '}
            <span className="text-gradient">investment intelligence</span>
          </h1>

          <p className="mt-4 max-w-2xl text-base leading-relaxed text-slate-400">
            InvestorIQ AI takes the annual reports you already have and turns
            them into a searchable, analyzable investment research workspace.
            Upload a report and the platform converts, chunks, and embeds it
            into Azure AI Search, extracts the key financial metrics into
            PostgreSQL, and lets you ask grounded questions about the results.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              to="/ingestion"
              className="group inline-flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-brand-500 to-accent-500 px-6 py-3.5 text-sm font-semibold text-ink-950 shadow-glow transition hover:brightness-110"
            >
              <UploadCloud size={18} />
              Get Started with Ingestion
              <ArrowRight
                size={16}
                className="transition-transform group-hover:translate-x-0.5"
              />
            </Link>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700/60 bg-ink-800/40 px-5 py-3.5 text-sm font-medium text-slate-200 transition hover:border-brand-500/40 hover:text-brand-200"
            >
              <BarChart3 size={16} /> View Dashboard
            </Link>
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1.5">
              <CheckCircle2 size={14} className="text-brand-400" /> Azure AI Search indexing
            </span>
            <span className="inline-flex items-center gap-1.5">
              <CheckCircle2 size={14} className="text-brand-400" /> PostgreSQL KPI extraction
            </span>
            <span className="inline-flex items-center gap-1.5">
              <CheckCircle2 size={14} className="text-brand-400" /> GPT-grounded Q&A
            </span>
          </div>
        </div>
      </section>

      {/* Capabilities */}
      <section>
        <SectionHeading
          eyebrow="Capabilities"
          title="Everything you need to analyze reports"
          subtitle="Three connected pipelines turn static filings into working investment intelligence."
        />
        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {FEATURES.map((feature) => {
            const Icon = feature.icon
            return (
              <div
                key={feature.title}
                className="panel panel-hover flex flex-col gap-4 p-6"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500/20 to-accent-500/20 ring-1 ring-brand-500/30">
                  <Icon size={22} className="text-brand-300" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-100">
                    {feature.title}
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-400">
                    {feature.description}
                  </p>
                </div>
                <ul className="flex flex-col gap-1.5">
                  {feature.points.map((point) => (
                    <li
                      key={point}
                      className="flex items-center gap-2 text-[13px] text-slate-400"
                    >
                      <CheckCircle2 size={13} className="shrink-0 text-brand-400/80" />
                      {point}
                    </li>
                  ))}
                </ul>
                <Link
                  to={feature.cta.to}
                  className="mt-auto inline-flex items-center gap-1.5 text-sm font-medium text-brand-300 transition hover:text-brand-200"
                >
                  {feature.cta.label} <ArrowRight size={15} />
                </Link>
              </div>
            )
          })}
        </div>
      </section>

      {/* How it works */}
      <section>
        <SectionHeading
          eyebrow="How it works"
          title="From filing to insight in three steps"
          subtitle="No manual data entry. Upload, let the AI pipeline do the work, then explore."
        />
        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {STEPS.map((step) => {
            const Icon = step.icon
            return (
              <div key={step.step} className="panel flex flex-col gap-3 p-6">
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-ink-800/70 text-brand-300 ring-1 ring-slate-700/60">
                    <Icon size={20} />
                  </div>
                  <span className="text-3xl font-bold tracking-tight text-slate-700">
                    {step.step}
                  </span>
                </div>
                <h3 className="text-base font-semibold text-slate-100">
                  {step.title}
                </h3>
                <p className="text-sm leading-relaxed text-slate-400">{step.text}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* CTA band */}
      <section className="panel relative overflow-hidden p-8 text-center sm:p-10">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-brand-500/10 via-transparent to-accent-500/10" />
        <div className="relative flex flex-col items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500 shadow-glow">
            <Rocket size={26} className="text-ink-950" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-50 sm:text-3xl">
            Ready to analyze your first report?
          </h2>
          <p className="max-w-xl text-sm leading-relaxed text-slate-400">
            Upload a single annual report to see conversion, indexing, KPI
            extraction, and grounded Q&A in action — end to end.
          </p>
          <Link
            to="/ingestion"
            className="group inline-flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-brand-500 to-accent-500 px-6 py-3.5 text-sm font-semibold text-ink-950 shadow-glow transition hover:brightness-110"
          >
            <UploadCloud size={18} />
            Get Started with Ingestion
            <ArrowRight
              size={16}
              className="transition-transform group-hover:translate-x-0.5"
            />
          </Link>
        </div>
      </section>
    </div>
  )
}

function SectionHeading({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow: string
  title: string
  subtitle: string
}) {
  return (
    <div className="mb-6 max-w-2xl">
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-widest text-brand-400">
        {eyebrow}
      </p>
      <h2 className="text-2xl font-bold tracking-tight text-slate-50">
        {title}
      </h2>
      <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{subtitle}</p>
    </div>
  )
}