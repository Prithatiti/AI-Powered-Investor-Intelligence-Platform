import { useRef, useState } from 'react'
import type { DragEvent, ReactNode } from 'react'
import {
  CheckCircle2,
  File as FileIcon,
  FileCheck2,
  FileText,
  UploadCloud,
  X,
} from 'lucide-react'

import { Pill } from '../components/ui'
import { api } from '../lib/api'
import type { UploadResponse } from '../types'

const ALLOWED = ['.pdf', '.md', '.txt']
const FILENAME_RE = /^(\d{4})_(.+)$/

type Status =
  | { state: 'idle' }
  | { state: 'uploading'; percent: number }
  | { state: 'done'; result: UploadResponse }
  | { state: 'error'; message: ReactNode }

function extOf(name: string): string {
  return name.slice(name.lastIndexOf('.')).toLowerCase()
}

export default function Ingestion() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [status, setStatus] = useState<Status>({ state: 'idle' })

  const acceptFile = (candidate: File) => {
    const name = candidate.name
    setStatus({ state: 'idle' })

    const invalidExt = !ALLOWED.includes(extOf(name))
    if (invalidExt) {
      setStatus({
        state: 'error',
        message: `"${name}" is not supported. Upload a PDF, Markdown, or text file.`,
      })
      setFile(null)
      return
    }

    if (!FILENAME_RE.test(name)) {
      setStatus({
        state: 'error',
        message: (
          <>
            Invalid filename{' '}
            <code className="rounded bg-ink-700/70 px-1.5 py-0.5 text-brand-300">
              "{name}"
            </code>
            . Use the format{' '}
            <code className="rounded bg-ink-700/70 px-1.5 py-0.5 text-brand-300">
              &lt;year&gt;_&lt;company&gt;
            </code>
            , e.g. <em>2024_Apple.pdf</em>.
          </>
        ),
      })
      setFile(null)
      return
    }

    setFile(candidate)
  }

  async function upload() {
    if (!file || status.state === 'uploading') return
    setStatus({ state: 'uploading', percent: 0 })
    try {
      const result = await api.upload(file, (percent) =>
        setStatus({ state: 'uploading', percent }),
      )
      setStatus({ state: 'done', result })
      setFile(null)
    } catch (err) {
      setStatus({
        state: 'error',
        message: err instanceof Error ? err.message : 'Upload failed.',
      })
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) acceptFile(dropped)
  }

  return (
    <div className="flex flex-col gap-8">
      <header>
        <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-brand-400">
          Pipeline intake
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-slate-50 sm:text-4xl">
          Ingest <span className="text-gradient">Reports</span>
        </h1>
        <p className="mt-1.5 max-w-2xl text-sm text-slate-400">
          Upload an annual report. It will be converted, chunked, embedded into
          Azure AI Search, and its financial metrics extracted into PostgreSQL.
        </p>
      </header>

      {/* Steps preview */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          { title: '01 · Convert', text: 'PDF → Markdown for LLM processing' },
          { title: '02 · Index', text: 'Semantic chunks → Azure AI Search' },
          { title: '03 · Extract', text: 'KPIs & risks → PostgreSQL' },
        ].map((step) => (
          <div key={step.title} className="panel p-4">
            <p className="text-sm font-semibold text-slate-200">{step.title}</p>
            <p className="mt-1 text-xs text-slate-500">{step.text}</p>
          </div>
        ))}
      </div>

      {/* Dropzone */}
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`panel relative flex min-h-[260px] cursor-pointer flex-col items-center justify-center gap-4 px-6 text-center transition-all ${
          dragOver
            ? 'border-brand-500/60 bg-brand-500/5 shadow-glow'
            : 'hover:border-brand-500/30'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED.join(',')}
          className="hidden"
          onChange={(e) => {
            const selected = e.target.files?.[0]
            if (selected) acceptFile(selected)
            e.target.value = ''
          }}
        />
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500/20 to-accent-500/20 ring-1 ring-brand-500/30">
          <UploadCloud size={30} className="text-brand-300" />
        </div>
        <div>
          <p className="text-base font-semibold text-slate-100">
            {dragOver ? 'Drop the report here' : 'Drag & drop a report, or click to browse'}
          </p>
          <p className="mt-1 text-sm text-slate-400">
            Accepts .pdf · .md · .txt — up to 50 MB
          </p>
        </div>
        <Pill tone="sky" className="!-mt-0">
          Required name format: <span className="font-mono">2024_Apple.pdf</span>
        </Pill>
      </div>

      {/* Selected / result card */}
      {(file || status.state !== 'idle') && (
        <div className="panel p-5">
          {status.state === 'uploading' ? (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 animate-spin rounded-full border-2 border-slate-700 border-t-brand-400" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-200">
                    Processing your report…
                  </p>
                  <p className="text-xs text-slate-500">
                    Converting, chunking, indexing, and saving metrics to
                    PostgreSQL — this can take a minute.
                  </p>
                </div>
                <div className="text-lg font-bold text-brand-300">
                  {status.percent}%
                </div>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-brand-500 to-accent-500 transition-all duration-200"
                  style={{ width: `${status.percent}%` }}
                />
              </div>
            </div>
          ) : status.state === 'done' ? (
            <div className="flex flex-col gap-3">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-500/10 text-brand-400">
                  <CheckCircle2 size={22} />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-emerald-300">
                    {status.result.message}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    <FileText size={12} className="mr-1 inline" />
                    {status.result.filename} · {status.result.chunks_indexed} chunks indexed
                    into Azure AI Search
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setStatus({ state: 'idle' })}
                  className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700/60 text-slate-400 transition hover:text-slate-200"
                >
                  <X size={16} />
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                <Pill tone="emerald">Indexed to vector store</Pill>
                <Pill tone="amber">Metrics persisted to PostgreSQL</Pill>
              </div>
            </div>
          ) : status.state === 'error' ? (
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-500/10 text-rose-400">
                <FileCheck2 size={22} />
              </div>
              <div className="flex-1 text-sm leading-relaxed text-rose-300">
                {status.message}
              </div>
              <button
                type="button"
                onClick={() => setStatus({ state: 'idle' })}
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700/60 text-slate-400 transition hover:text-slate-200"
              >
                <X size={16} />
              </button>
            </div>
          ) : (
            file && (
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-500/10 text-accent-400">
                  <FileIcon size={20} />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-200">{file.name}</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {(file.size / 1024 / 1024).toFixed(2)} MB · ready to upload
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => upload()}
                    className="rounded-xl bg-gradient-to-r from-brand-500 to-accent-500 px-5 py-2.5 text-sm font-semibold text-ink-950 shadow-glow transition hover:brightness-110"
                  >
                    Upload &amp; Index
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setFile(null)
                      setStatus({ state: 'idle' })
                    }}
                    className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-700/60 text-slate-400 transition hover:text-slate-200"
                  >
                    <X size={16} />
                  </button>
                </div>
              </div>
            )
          )}
        </div>
      )}
    </div>
  )
}