import { useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { Bot, Download, RotateCcw, Send, Sparkles, User } from 'lucide-react'

import { Spinner } from '../components/ui'
import { api } from '../lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const WELCOME_MESSAGE: Message = {
  role: 'assistant',
  content:
    "Welcome to InvestorIQ AI — your intelligent financial research assistant. Explore company performance, uncover key financial insights, analyze risks and growth drivers, and ask questions about your ingested reports to make faster, data-driven investment decisions.",
}

const SUGGESTIONS = [
  'Why did revenue increase this year?',
  'What are the major risks facing the company?',
  'What were the key growth drivers?',
  'Compare capital allocation across the reports.',
  'What is the executive-level financial outlook?',
]

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function renderInline(text: string): string {
  return escapeHtml(text)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="rounded bg-ink-700/70 px-1 py-0.5 text-[12px] text-brand-300">$1</code>')
}

function renderBlocks(markdown: string): ReactNode {
  const lines = markdown.split('\n')
  const blocks: ReactNode[] = []
  let key = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]!

    // Code fence
    if (line.trim().startsWith('```')) {
      const fence: string[] = []
      i++
      while (i < lines.length && !lines[i]!.trim().startsWith('```')) {
        fence.push(lines[i]!)
        i++
      }
      blocks.push(
        <pre
          key={`pre-${key++}`}
          className="my-2 overflow-x-auto rounded-lg border border-slate-800/70 bg-ink-950/80 px-3 py-2 text-[12.5px] text-slate-300"
        >
          <code>{escapeHtml(fence.join('\n'))}</code>
        </pre>,
      )
      continue
    }

    // Unordered list
    if (/^(\s*[-*•]\s+)/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^(\s*[-*•]\s+)/.test(lines[i]!)) {
        items.push(lines[i]!.replace(/^(\s*[-*•]\s+)/, ''))
        i++
      }
      i--
      blocks.push(
        <ul key={`ul-${key++}`} className="my-2 flex flex-col gap-1.5">
          {items.map((item, j) => (
            <li key={j} className="flex gap-2.5 text-[13px] leading-relaxed">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" />
              <span dangerouslySetInnerHTML={{ __html: renderInline(item) }} />
            </li>
          ))}
        </ul>,
      )
      continue
    }

    // Ordered list
    if (/^(\s*\d+[.)]\s+)/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^(\s*\d+[.)]\s+)/.test(lines[i]!)) {
        items.push(lines[i]!.replace(/^(\s*\d+[.)]\s+)/, ''))
        i++
      }
      i--
      blocks.push(
        <ol key={`ol-${key++}`} className="my-2 flex list-decimal flex-col gap-1.5 pl-5 text-[13px]">
          {items.map((item, j) => (
            <li key={j}>
              <span dangerouslySetInnerHTML={{ __html: renderInline(item) }} />
            </li>
          ))}
        </ol>,
      )
      continue
    }

    if (!line.trim()) continue
    blocks.push(
      <p key={`p-${key++}`} className="mb-2 text-[13px] leading-relaxed">
        <span dangerouslySetInnerHTML={{ __html: renderInline(line) }} />
      </p>,
    )
  }

  return blocks
}

function buildTranscript(
  messages: Message[],
  company: string,
  year: string,
): string {
  const date = new Date().toISOString()
  const lines: string[] = []

  lines.push('InvestorIQ AI — Conversation Transcript')
  lines.push('=======================================')
  lines.push('')
  lines.push(`Generated: ${date}`)
  const scopeName =
    company === '' ? 'No company selected' : company
  lines.push(
    `Scope: ${scopeName}${year ? ` · Year: ${year}` : ''}`,
  )
  lines.push(
    '=======================================',
  )
  lines.push('')

  for (const msg of messages) {
    const speaker =
      msg.role === 'user' ? 'USER' : 'AI ASSISTANT'
    lines.push(`${speaker}:`)
    lines.push('')
    lines.push(msg.content.trim())
    lines.push('')
    lines.push('---')
    lines.push('')
  }

  return lines.join('\n')
}

function downloadTranscript(
  messages: Message[],
  company: string,
  year: string,
): void {
  const content = buildTranscript(messages, company, year)
  const blob = new Blob([content], {
    type: 'text/plain;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  const date = new Date().toISOString().slice(0, 10)
  anchor.href = url
  anchor.download = `investoriq-conversation-${date}.txt`
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

export default function Research() {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE])
  const [input, setInput] = useState('')
  const [company, setCompany] = useState('')
  const [companies, setCompanies] = useState<string[]>([])
  const [year, setYear] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, busy])

  useEffect(() => {
    api
      .metrics()
      .then((res) => {
        const names = [
          ...new Set(res.metrics.map((m) => m.company)),
        ].sort()
        setCompanies(names)
      })
      .catch(() => {})
  }, [])

  async function send(text: string, asSuggestion = false) {
    const question = asSuggestion ? text : text.trim()
    if (!question || busy) return

    const message: Message = { role: 'user', content: question }
    setMessages((prev) => [...prev, message])
    setInput('')
    setError(null)
    setBusy(true)

    try {
      const res = await api.chat({
        question,
        company: company === 'All Companies' || !company ? null : company,
        year: year ? Number(year) : null,
      })
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.answer },
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get an answer.')
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            'Sorry, I could not generate an answer right now. Please try again.',
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    void send(input)
  }

  const companySelected = company !== ''

  return (
    <div className="flex h-[calc(100vh-6.5rem)] flex-col">
      <header className="mx-auto mb-5 w-full max-w-3xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-brand-400">
              Conversational analysis
            </p>
            <h1 className="flex items-center gap-3 text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500/20 to-accent-500/20 ring-1 ring-brand-500/30">
                <Bot size={24} className="text-brand-300" />
              </span>
              AI <span className="text-gradient">Research</span>
            </h1>
            <p className="mt-1.5 max-w-2xl text-sm text-slate-400">
              Ask grounded questions about any ingested annual report. Answers
              are retrieved from the Azure AI Search index and generated from
              the underlying evidence.
            </p>
          </div>
          {messages.length > 1 && (
            <button
              type="button"
              onClick={() =>
                downloadTranscript(messages, company, year)
              }
              title="Download conversation transcript"
              className="mt-11 inline-flex shrink-0 items-center gap-2 rounded-lg border border-slate-700/60 bg-ink-800/60 px-3 py-2 text-xs font-medium text-slate-300 transition hover:border-brand-500/40 hover:text-brand-200"
            >
              <Download size={14} />
              <span className="hidden sm:inline">
                Download Conversation
              </span>
            </button>
          )}
        </div>
      </header>

      <div className="panel mx-auto flex w-full max-w-3xl flex-1 flex-col overflow-hidden">
        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-800/60 px-4 py-3">
          <Sparkles size={15} className="text-brand-400" />
          <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Scope
          </span>
          <select
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            className="w-48 rounded-lg border border-slate-600/70 bg-ink-700/70 px-3 py-1.5 text-sm text-slate-100 focus:border-brand-500/60 focus:outline-none [color-scheme:dark]"
          >
            <option value="" disabled className="bg-ink-900 text-slate-400">
              Select company…
            </option>
            <option value="All Companies" className="bg-ink-900 text-slate-100">
              All Companies
            </option>
            {companies.map((c) => (
              <option key={c} value={c} className="bg-ink-900 text-slate-100">
                {c}
              </option>
            ))}
          </select>
          <input
            value={year}
            onChange={(e) => setYear(e.target.value.replace(/\D/g, '').slice(0, 4))}
            placeholder="Year (e.g. 2024)"
            inputMode="numeric"
            className="w-32 rounded-lg border border-slate-700/60 bg-ink-800/60 px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-500 focus:border-brand-500/50 focus:outline-none"
          />
          {year && (
            <button
              type="button"
              onClick={() => setYear('')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700/60 px-2.5 py-1.5 text-xs text-slate-400 transition hover:text-slate-200"
            >
              <RotateCcw size={13} /> Clear
            </button>
          )}
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 space-y-5 overflow-y-auto px-4 py-5 sm:px-6">
          {messages.length === 1 && !busy ? (
            <div className="flex min-h-full flex-col items-center justify-center gap-6 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500/20 to-accent-500/20 ring-1 ring-brand-500/30">
                <Bot size={30} className="text-brand-300" />
              </div>
              <div className="max-w-md">
                <h2 className="text-lg font-semibold text-slate-200">
                  {companySelected
                    ? 'Ask anything about your reports'
                    : 'Select a company to get started'}
                </h2>
                <p className="mx-auto mt-2 text-sm leading-relaxed text-slate-400">
                  {WELCOME_MESSAGE.content}
                </p>
              </div>
              {companySelected && (
                <div className="flex max-w-2xl flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => void send(s, true)}
                      className="rounded-full border border-slate-700/60 bg-ink-800/50 px-3.5 py-1.5 text-[13px] text-slate-300 transition hover:border-brand-500/40 hover:text-brand-200"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <>
              {messages.map((msg, index) => (
                <MessageBubble key={index} message={msg} />
              ))}

              {busy && (
                <div className="flex items-start gap-3">
                  <Avatar role="assistant" />
                  <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-slate-800/70 bg-ink-800/50 px-4 py-3">
                    <Spinner size={16} />
                    <span className="text-sm text-slate-400">
                      Retrieving context &amp; generating…
                    </span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Error banner */}
        {error && (
          <div className="mx-4 mb-2 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2.5 text-sm text-rose-300">
            {error}
          </div>
        )}

        {/* Composer */}
        <form
          onSubmit={onSubmit}
          className="flex items-end gap-2 border-t border-slate-800/60 bg-ink-900/40 p-3"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                if (companySelected) void send(input)
              }
            }}
            rows={1}
            placeholder={
              companySelected
                ? 'Ask a question about the reports…'
                : 'Select a company to start asking…'
            }
            className="max-h-32 min-h-[42px] flex-1 resize-none rounded-xl border border-slate-700/60 bg-ink-800/60 px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:border-brand-500/50 focus:outline-none"
          />
          <button
            type="submit"
            disabled={!companySelected || !input.trim() || busy}
            className="flex h-[42px] shrink-0 items-center gap-2 rounded-xl bg-gradient-to-r from-brand-500 to-accent-500 px-5 text-sm font-semibold text-ink-950 shadow-glow transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send size={16} />
            <span className="hidden sm:inline">Ask</span>
          </button>
        </form>
      </div>
    </div>
  )
}

function Avatar({ role }: { role: 'user' | 'assistant' }) {
  if (role === 'assistant') {
    return (
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500">
        <Bot size={18} className="text-ink-950" />
      </div>
    )
  }
  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-ink-700">
      <User size={18} className="text-slate-300" />
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div className="flex items-start gap-3">
      <Avatar role={message.role} />
      <div
        className={
          isUser
            ? 'rounded-2xl rounded-tl-sm border border-slate-700/60 bg-ink-800/70 px-4 py-2.5 text-sm text-slate-100'
            : 'w-full rounded-2xl rounded-tl-sm border border-slate-800/70 bg-ink-850/70 px-4 py-3'
        }
      >
        {isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        ) : (
          <div className="text-slate-200">{renderBlocks(message.content)}</div>
        )}
      </div>
    </div>
  )
}