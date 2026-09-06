import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Menu,
  MessagesSquare,
  PanelLeftClose,
  PanelLeftOpen,
  TrendingUp,
  UploadCloud,
  X,
} from 'lucide-react'
import type { ReactNode } from 'react'

import { api } from '../lib/api'

const NAV_ITEMS = [
  {
    to: '/ingestion',
    label: 'Ingest Reports',
    short: 'Ingest',
    icon: UploadCloud,
  },
  {
    to: '/',
    label: 'Dashboard',
    short: 'Dash',
    icon: LayoutDashboard,
  },
  {
    to: '/research',
    label: 'AI Research',
    short: 'Chat',
    icon: MessagesSquare,
  },
]

const STORAGE_KEY = 'investoriq.sidebar.collapsed'

function Brand({ collapsed }: { collapsed: boolean }) {
  return (
    <NavLink
      to="/"
      className="flex items-center gap-3"
      title={collapsed ? 'InvestorIQ' : undefined}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500 shadow-glow">
        <TrendingUp size={22} className="text-ink-950" strokeWidth={2.5} />
      </div>
      {!collapsed && (
        <div className="leading-tight">
          <p className="text-[15px] font-bold tracking-tight text-slate-100">
            InvestorIQ
          </p>
          <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500">
            AI Intelligence
          </p>
        </div>
      )}
    </NavLink>
  )
}

function HealthDot({ collapsed }: { collapsed: boolean }) {
  const [ok, setOk] = useState<boolean | null>(null)

  useEffect(() => {
    let active = true
    api
      .health()
      .then(() => active && setOk(true))
      .catch(() => active && setOk(false))
    return () => {
      active = false
    }
  }, [])

  const dotClass =
    ok === null
      ? 'animate-pulse bg-amber-400'
      : ok
        ? 'bg-emerald-400'
        : 'bg-rose-400'
  const label = ok === null ? 'Checking…' : ok ? 'API Online' : 'API Offline'

  if (collapsed) {
    return (
      <span
        className="inline-flex w-full items-center justify-center rounded-lg border border-slate-700/50 bg-ink-800/50 px-2 py-2"
        title={label}
      >
        <span className={`h-2 w-2 rounded-full ${dotClass}`} />
      </span>
    )
  }

  return (
    <span className="inline-flex w-full items-center gap-2 rounded-lg border border-slate-700/50 bg-ink-800/50 px-3 py-2 text-xs text-slate-400">
      <span className={`h-2 w-2 rounded-full ${dotClass}`} />
      {label}
    </span>
  )
}

export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem(STORAGE_KEY, next ? '1' : '0')
      } catch {
        /* ignore storage errors */
      }
      return next
    })
  }

  const navContent = (isCollapsed: boolean): ReactNode => (
    <>
      <nav className="flex flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all ${
                  isCollapsed ? 'justify-center px-3' : ''
                } ${
                  isActive
                    ? 'bg-brand-500/10 text-brand-300 ring-1 ring-brand-500/30'
                    : 'text-slate-400 hover:bg-ink-800/60 hover:text-slate-200'
                }`
              }
            >
              <Icon size={18} strokeWidth={2} />
              {!isCollapsed && (
                <span className="hidden lg:inline">{item.label}</span>
              )}
              <span className="lg:hidden">{item.short}</span>
            </NavLink>
          )
        })}
      </nav>
      <div className="mt-auto flex flex-col gap-3">
        <HealthDot collapsed={isCollapsed} />
        {!isCollapsed && (
          <p className="px-1 text-[11px] text-slate-600">
            v0.1.0 · Powered by Azure OpenAI &amp; AI Search
          </p>
        )}
      </div>
    </>
  )

  return (
    <div className="grid-bg min-h-screen">
      {/* Desktop sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 hidden flex-col gap-8 border-r border-slate-800/60 bg-ink-900/80 backdrop-blur-xl transition-[width,padding] duration-300 lg:flex ${
          collapsed ? 'w-20 px-3 py-5' : 'w-64 p-5'
        }`}
      >
        <div
          className={`flex w-full items-center ${
            collapsed ? 'flex-col gap-5' : 'justify-between gap-3'
          }`}
        >
          <Brand collapsed={collapsed} />
          <button
            type="button"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            onClick={toggleCollapsed}
            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-700/50 text-slate-400 transition hover:text-slate-200 ${
              collapsed ? 'mx-auto' : ''
            }`}
          >
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
        </div>
        {navContent(collapsed)}
      </aside>

      {/* Mobile top bar */}
      <div className="sticky top-0 z-40 flex items-center justify-between border-b border-slate-800/60 bg-ink-900/90 px-4 py-3 backdrop-blur-xl lg:hidden">
        <Brand collapsed={false} />
        <button
          type="button"
          aria-label="Toggle navigation"
          onClick={() => setMenuOpen((open) => !open)}
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-700/50 text-slate-300"
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setMenuOpen(false)}
          />
          <div className="relative flex w-64 flex-col gap-8 border-r border-slate-800/60 bg-ink-900 p-5">
            <Brand collapsed={false} />
            {navContent(false)}
          </div>
        </div>
      )}

      {/* Main content */}
      <main
        className={`px-4 pb-16 pt-6 transition-[margin] duration-300 sm:px-6 md:px-8 ${
          collapsed ? 'lg:ml-20' : 'lg:ml-64'
        }`}
      >
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}