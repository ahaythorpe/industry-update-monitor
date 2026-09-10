export type Flag = 'ACT' | 'KNOW' | 'NOTE'
export type LinkExactness = 'exact' | 'fallback' | 'broad'

export type DigestItem = {
  id: string
  title: string
  teaser: string
  link: string
  source_name: string
  flag: Flag
  topic: string
  is_read: boolean
  created_at: string
  ai_summary?: string | null
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
    title: input.title,
    teaser: input.teaser || '',
    link: input.link,
    source_name: input.source_name,
    flag: input.flag,
    topic: input.topic,
    is_read: input.is_read ?? false,
    created_at: input.created_at || new Date().toISOString(),
    ai_summary: input.ai_summary ?? null,
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
