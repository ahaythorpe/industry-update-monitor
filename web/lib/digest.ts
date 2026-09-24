export type Flag = 'ACT' | 'KNOW' | 'NOTE'
export type LinkExactness = 'exact' | 'fallback' | 'broad'

export type DigestItem = {
  id: string
  // The six-character handle a briefing round trip is matched on. Written by
  // export_json; kept here so a briefing downloaded from the dashboard imports
  // through `--import-summaries` exactly like one written by the CLI.
  ref?: string | null
  title: string
  teaser: string
  // The fuller teaser the feed supplied, used for summarising. `teaser` is the
  // shortened version the dashboard shows on a card.
  brief_text?: string | null
  // Whether brief_text is the article the feed carried or only its teaser.
  body_source?: 'feed_content' | 'feed_summary' | null
  link: string
  source_name: string
  // How the item reached us: a public feed, or a newsletter in the Gmail
  // label. A newsletter's link goes to your own mailbox, not a public page.
  intake?: 'rss' | 'email'
  flag: Flag
  topic: string
  is_read: boolean
  created_at: string
  ai_summary?: string | null
  // Where a summary came from. "manual" means it was written in a web AI tool
  // and pasted back by hand — never presented as something this tool produced.
  ai_source?: string | null
  ai_generated_at?: string | null
  confidence?: number | null
  link_exactness?: LinkExactness
}

export type DigestSource = {
  name: string
  home: string
  count: number
}

// Section pages a bookmark-and-check source points at: landing pages that list
// stories rather than being one. Matched as the LAST path segment, never as a
// substring — "/news/" appears inside plenty of real article URLs, and matching
// it anywhere demoted 13 of 50 real articles (every Financial Standard and
// Riskinfo story) to "fallback", where the default filter hid them.
const SECTION_SEGMENTS = new Set([
  'news',
  'newsroom',
  'media-releases',
  'media-release',
  'consultation',
  'consultations',
  'search',
  'statistics',
  'people',
  'find-a-document',
  'what-to-expect',
  'publications',
])

// An article slug: hyphenated words, or one long word. "/news/12345" or
// "/about" is a section or an index, not a story.
function looksLikeArticleSlug(segment: string): boolean {
  return segment.includes('-') || segment.length > 12
}

export function classifyLinkExactness(url: string): LinkExactness {
  let parsed: URL
  try {
    parsed = new URL((url || '').trim())
  } catch {
    return 'broad'
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return 'broad'
  }

  const segments = parsed.pathname.split('/').filter(Boolean)
  if (segments.length === 0) {
    // The bare home page: all we have for a source with no feed.
    return 'broad'
  }

  const last = segments[segments.length - 1].toLowerCase()
  if (SECTION_SEGMENTS.has(last)) {
    return 'fallback'
  }
  if (!segments.some(looksLikeArticleSlug)) {
    return 'fallback'
  }
  return 'exact'
}

export function normalizeIncomingItem(input: Partial<DigestItem> & Pick<DigestItem, 'title' | 'link' | 'source_name' | 'flag' | 'topic'>): DigestItem {
  return {
    id: input.id || `item-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    // Never invented: the ref is a hash of the link computed by the monitor,
    // so an item that arrived without one has no ID a reply could be matched
    // back to, and the briefing builder leaves it out rather than guessing.
    ref: input.ref ?? null,
    title: input.title,
    teaser: input.teaser || '',
    brief_text: input.brief_text ?? null,
    body_source: input.body_source ?? null,
    link: input.link,
    source_name: input.source_name,
    intake: input.intake || 'rss',
    flag: input.flag,
    topic: input.topic,
    is_read: input.is_read ?? false,
    created_at: input.created_at || new Date().toISOString(),
    ai_summary: input.ai_summary ?? null,
    ai_source: input.ai_source ?? null,
    ai_generated_at: input.ai_generated_at ?? null,
    confidence: input.confidence ?? null,
    link_exactness: classifyLinkExactness(input.link),
  }
}

// The digest itself is loaded at request time by lib/digest-server.ts, so a
// fresh `python src/monitor.py --json` is picked up without a rebuild. These
// helpers are pure: they take the items and filter them.

// Server-side counts only. "Read" is per-browser state (see the dashboard's
// useReadItems), so an unread count from here would always equal the total.
export function getStats(items: DigestItem[]) {
  return {
    total: items.length,
    act: items.filter((item) => item.flag === 'ACT').length,
    know: items.filter((item) => item.flag === 'KNOW').length,
    note: items.filter((item) => item.flag === 'NOTE').length,
  }
}

export function getItems(
  source: DigestItem[],
  options?: {
    flag?: string
    source?: string
    limit?: number
    query?: string
    dateRange?: 'week' | 'month' | 'all'
    exactness?: LinkExactness | 'all'
  }
) {
  let items = [...source]

  // Default to everything, the same as the dashboard: hiding "fallback" links
  // by default silently dropped a fifth of the digest from /api/items.
  const requiredExactness = options?.exactness ?? 'all'
  if (requiredExactness !== 'all') {
    items = items.filter((item) => (item.link_exactness || 'broad') === requiredExactness)
  }

  if (options?.flag) {
    items = items.filter((item) => item.flag === options.flag)
  }

  if (options?.source) {
    const name = options.source.toLowerCase()
    items = items.filter((item) => item.source_name.toLowerCase() === name)
  }

  if (options?.query) {
    const query = options.query.toLowerCase()
    items = items.filter(
      (item) =>
        item.title.toLowerCase().includes(query) ||
        item.teaser.toLowerCase().includes(query) ||
        item.source_name.toLowerCase().includes(query)
    )
  }

  if (options?.dateRange && options.dateRange !== 'all') {
    const days = options.dateRange === 'week' ? 7 : 30
    const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000)
    items = items.filter((item) => new Date(item.created_at) >= cutoff)
  }

  if (options?.limit) {
    items = items.slice(0, options.limit)
  }

  return items
}

/**
 * Who wrote this summary, in words a reader can weigh.
 *
 * Mirrors summary_origin in src/email_sender.py. Never a bare "Summary": a
 * summary with no origin reads as this tool's own work, and this tool does not
 * write summaries — they come from you, or from a model you ran.
 */
export function summaryOrigin(source?: string | null): string {
  if (source === 'manual') return 'Summarised by hand'
  if (source?.startsWith('ollama:')) {
    return `Summarised by a local model (${source.slice('ollama:'.length)})`
  }
  if (source) return `Summarised by ${source}`
  return 'Summary, origin not recorded'
}

/**
 * A summary's dot points. The local model writes them on one line, each
 * starting "• ", with the key fact in **bold**; an older one-sentence summary
 * is a single point. Mirrors summary_points in src/email_sender.py.
 */
export function summaryPoints(summary?: string | null): string[] {
  const points = (summary || '')
    .split(/\s*•\s*/)
    .map((point) => point.trim())
    .filter(Boolean)
  return points
}

/** Split a point into plain and **bold** runs, for rendering without HTML. */
export function boldRuns(point: string): { text: string; bold: boolean }[] {
  return point
    .split(/(\*\*.+?\*\*)/)
    .filter(Boolean)
    .map((run) =>
      run.startsWith('**') && run.endsWith('**') && run.length > 4
        ? { text: run.slice(2, -2), bold: true }
        : { text: run, bold: false }
    )
}
