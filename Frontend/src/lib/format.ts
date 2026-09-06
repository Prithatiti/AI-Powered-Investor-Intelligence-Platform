/** Formatting / parsing helpers for financial metric strings. */

const SCALES: Record<string, number> = {
  thousand: 1e-9,
  k: 1e-9,
  million: 1e-3,
  mn: 1e-3,
  m: 1e-3,
  billion: 1,
  bn: 1,
  b: 1,
  trillion: 1e3,
  t: 1e3,
}

/**
 * Parse a financial string such as "$394.3 billion" or "93,737" into a
 * number expressed in **billions**. Returns `null` when unparseable.
 *
 * Reports store figures in a mixture of units: some include a scale word
 * ("$394.3 billion"), others give bare amounts in millions ("$ 97,690").
 * When no scale is present, values >= 1000 are treated as millions and
 * normalised to billions so charts compare like-for-like.
 */
export function parseMoney(value: string | null | undefined): number | null {
  if (!value) return null
  const str = String(value).trim()
  const match = str.match(/([\d,]+(?:\.\d+)?)\s*(billion|trillion|million|thousand|[btmkn]{1,2})?\b.*/i)
  if (!match) return null
  const amount = parseFloat(match[1]!.replace(/,/g, ''))
  if (Number.isNaN(amount)) return null
  const scale = match[2] ? SCALES[match[2].toLowerCase()] ?? 1 : 1
  let billions = (amount * scale)
  // No explicit unit: assume bare amounts >= 1000 are expressed in millions.
  if (!match[2] && billions >= 1000) billions /= 1000
  return billions
}

/** Format a number (already in billions) back to a compact label, e.g. "394.3B". */
export function formatCompactBn(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '—'
  if (Math.abs(value) >= 100) return `$${value.toFixed(1)}B`
  if (Math.abs(value) >= 1) return `$${value.toFixed(2)}B`
  return `$${(value * 1000).toFixed(1)}M`
}

/** Parse a JSON-encoded string list (e.g. "[\"a\",\"b\"]") into an array. */
export function parseStringList(value: string | null | undefined): string[] {
  if (!value) return []
  try {
    const parsed = JSON.parse(value) as unknown
    if (Array.isArray(parsed)) {
      return parsed.map((item) => String(item)).filter(Boolean)
    }
    return [String(parsed)]
  } catch {
    // Fallback: split on newlines / bullets.
    return value
      .split(/\n+|\s*[-•*]\s+/)
      .map((item) => item.trim())
      .filter(Boolean)
  }
}

/** Shorten a company name for compact chips. */
export function shortName(company: string): string {
  const name = String(company).trim()
  const tokens = name.split(/\s+/)
  if (tokens.length === 1) return name
  // "Space X" -> "Space X", keep two tokens if the second is single-letter.
  const [first, second] = tokens
  return second && second.length <= 2 ? `${first} ${second}` : name
}

/** Monogram initials for a company, e.g. "Apple" -> "A". */
export function initials(company: string): string {
  const tokens = String(company)
    .trim()
    .split(/\s+/)
  if (tokens.length === 1) return tokens[0]!.slice(0, 2).toUpperCase()
  return (
    tokens
      .slice(0, 2)
      .map((t) => t[0])
      .join('')
      .toUpperCase()
  )
}