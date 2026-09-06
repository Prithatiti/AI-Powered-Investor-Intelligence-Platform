import type {
  ChatPayload,
  ChatResponse,
  HealthResponse,
  MetricsResponse,
  UploadResponse,
} from '../types'

const API_BASE: string = import.meta.env.VITE_API_URL ?? '/api'

async function parseError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string | unknown }
    if (typeof body.detail === 'string') return body.detail
    return `Request failed (${res.status})`
  } catch {
    return `Request failed (${res.status})`
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, init)
  } catch {
    throw new Error(
      'Unable to reach the InvestorIQ API. Is the backend running?',
    )
  }
  if (!res.ok) throw new Error(await parseError(res))
  return (await res.json()) as T
}

export const api = {
  health: () => request<HealthResponse>('/health'),

  metrics: () => request<MetricsResponse>('/metrics'),

  chat: (payload: ChatPayload) =>
    request<ChatResponse>('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  upload: (
    file: File,
    onProgress?: (percent: number) => void,
  ): Promise<UploadResponse> => {
    const body = new FormData()
    body.append('file', file)

    return new Promise((resolve, reject) => {
      fetch(`${API_BASE}/ingestion/upload`, { method: 'POST', body })
        .then(async (res) => {
          if (!res.ok) throw new Error(await parseError(res))
          if (!res.body) throw new Error('Upload failed: unexpected response.')

          const reader = res.body.getReader()
          const decoder = new TextDecoder()
          let buffer = ''
          let complete: UploadResponse | null = null

          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true })

            // SSE frames are separated by a blank line.
            const frames = buffer.split(/\r?\n\r?\n/)
            buffer = frames.pop() ?? ''

            for (const frame of frames) {
              if (!frame.trim()) continue

              let event = 'message'
              const dataLines: string[] = []
              for (const line of frame.split(/\r?\n/)) {
                if (line.startsWith('event:')) {
                  event = line.slice('event:'.length).trim()
                } else if (line.startsWith('data:')) {
                  dataLines.push(line.slice('data:'.length).trim())
                }
              }
              if (!dataLines.length) continue

              let data: Record<string, unknown>
              try {
                data = JSON.parse(dataLines.join('\n')) as Record<
                  string,
                  unknown
                >
              } catch {
                continue
              }

              if (event === 'progress') {
                if (typeof data.percent === 'number') onProgress?.(data.percent)
              } else if (event === 'complete') {
                complete = data as unknown as UploadResponse
              } else if (event === 'error') {
                throw new Error(
                  typeof data.message === 'string'
                    ? data.message
                    : 'Upload failed.',
                )
              }
            }
          }

          if (!complete) {
            throw new Error('Upload failed: no confirmation from server.')
          }
          resolve(complete)
        })
        .catch((err) => reject(err))
    })
  },
}