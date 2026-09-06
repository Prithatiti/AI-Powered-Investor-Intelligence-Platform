import type { ReactNode } from 'react'
import { Loader2 } from 'lucide-react'

export function Spinner({ size = 20 }: { size?: number }) {
  return <Loader2 size={size} className="animate-spin text-brand-400" />
}

export function LoadingBlock({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-slate-400">
      <Spinner size={26} />
      <p className="text-sm">{label ?? 'Loading…'}</p>
    </div>
  )
}

export function ErrorBlock({ message }: { message: string }) {
  return (
    <div className="panel flex flex-col items-center justify-center gap-3 border-rose-500/30 px-6 py-14 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-rose-500/10 text-rose-400">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" x2="12" y1="8" y2="12" />
          <line x1="12" x2="12.01" y1="16" y2="16" />
        </svg>
      </div>
      <h3 className="font-semibold text-rose-300">Something went wrong</h3>
      <p className="max-w-md text-sm text-slate-400">{message}</p>
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="panel flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      {icon && (
        <div className="text-brand-400/80">{icon ?? <Spinner />}</div>
      )}
      <h3 className="text-lg font-semibold text-slate-200">{title}</h3>
      {description && (
        <p className="max-w-md text-sm leading-relaxed text-slate-400">
          {description}
        </p>
      )}
      {action}
    </div>
  )
}

export function SectionTitle({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold tracking-tight text-slate-100">
          {title}
        </h2>
        {subtitle && (
          <p className="mt-0.5 text-sm text-slate-400">{subtitle}</p>
        )}
      </div>
      {action}
    </div>
  )
}

const pillTones = {
  emerald: 'bg-brand-500/10 text-brand-300 border-brand-500/30',
  sky: 'bg-accent-500/10 text-accent-400 border-accent-500/30',
  amber: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  rose: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
  violet: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
  slate: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
} as const

export type PillTone = keyof typeof pillTones

export function Pill({
  children,
  tone = 'emerald',
  className = '',
}: {
  children: ReactNode
  tone?: PillTone
  className?: string
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${pillTones[tone]} ${className}`}
    >
      {children}
    </span>
  )
}