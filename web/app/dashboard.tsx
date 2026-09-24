'use client'

import { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import Link from 'next/link'
import { type DigestItem, type DigestSource, type Flag } from '@/lib/digest'
import {
  BRIEF_CHUNK,
  BRIEF_PROMPT,
  DEEP_CHUNK,
  DEEP_PROMPT,
  FALLBACK_TOPIC,
  type Grouping,
  briefingFilename,
  buildBriefingFiles,
  buildReadingFiles,
  combineBriefing,
  slug,
} from '@/lib/briefing'
import { buildZip } from '@/lib/zip'
import { bundleLinks, bundleLinksBySource, bundleReadme } from '@/lib/bundle'
import { boldRuns, summaryOrigin, summaryPoints } from '@/lib/digest'
import { formatDay, toDayKey } from '@/lib/utils'
import { Calendar } from '@/components/Calendar'
import { SettingsModal } from '@/components/SettingsModal'
import { PaywallModal } from '@/components/PaywallModal'
import { UnreachableSources } from '@/components/UnreachableSources'
import { CategoryBoard } from '@/components/CategoryBoard'
import type { GlossaryEntry } from '@/lib/glossary'

type Exactness = 'all' | 'exact' | 'fallback' | 'broad'
type DateRange = 'week' | 'month' | 'all'

type IntegrationStatus = { configured: boolean; detail: string }
type Status = {
  digest: { generated_at: string; items: number; sources: number }
  telegram: IntegrationStatus
  email: IntegrationStatus
  ai: IntegrationStatus
}

const flagMeta: Record<Flag, { chip: string; button: string }> = {
  ACT: {
    chip: 'border-red-500/40 bg-red-500/10 text-red-300',
    button: 'bg-red-600 text-white border border-red-500',
  },
  KNOW: {
    chip: 'border-orange-500/40 bg-orange-500/10 text-orange-300',
    button: 'bg-orange-600 text-white border border-orange-500',
  },
  NOTE: {
    chip: 'border-green-500/40 bg-green-500/10 text-green-300',
    button: 'bg-green-600 text-white border border-green-500',
  },
}

const exactnessMeta = {
  exact: { label: 'Exact', className: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' },
  fallback: { label: 'Section page', className: 'border-amber-500/40 bg-amber-500/10 text-amber-300' },
  broad: { label: 'Manual review', className: 'border-rose-500/40 bg-rose-500/10 text-rose-300' },
} as const

/**
 * How a downloaded briefing is split into files.
 *
 * There are only two things to split on, so there are two checkboxes rather
 * than one list of every combination. That list had to name the combinations
 * to be any use ("Category, then flag: Compliance · ACT, Regulation · ACT,
 * +12 more") and was unreadable by the time it did.
 *
 * Ticking both splits by category first, so the files read compliance-act.md.
 * The reverse nesting is still there on the command line as
 * `--group-by flag,topic` for anyone who wants to clear every ACT item first.
 */
const DIMENSIONS = [
  { key: 'topic' as const, label: 'Category', example: 'Compliance, Regulation, Super & tax…' },
  { key: 'flag' as const, label: 'Urgency', example: 'ACT, KNOW, NOTE' },
]

const FORMATS = [
  { value: 'zip', label: 'Zip — one file per group' },
  { value: 'md', label: 'Single Markdown file' },
] as const

type Format = (typeof FORMATS)[number]['value']

/*
 * Triage or detail. One prompt cannot do both: "one line each, only from the
 * teaser" is right for sorting fifty items and guarantees one-liners, which is
 * the opposite of what you want on the handful that matter.
 */
const DEPTHS = [
  { value: 'brief', label: 'Triage — one line each', prompt: BRIEF_PROMPT, chunk: BRIEF_CHUNK },
  { value: 'deep', label: 'Detailed — a short paragraph each', prompt: DEEP_PROMPT, chunk: DEEP_CHUNK },
  // No prompt: the summaries are already written, so this is for an AI (or a
  // person) to read, with each summary beside its link.
  { value: 'read', label: 'Finished summaries — ready to read', prompt: null, chunk: 0 },
] as const

type Depth = (typeof DEPTHS)[number]['value']

const READ_STORAGE_KEY = 'advice-monitor:read-items'
const THEME_STORAGE_KEY = 'advice-monitor:theme'

// Light or dark, remembered in this browser. Read through
// useSyncExternalStore like the read-items list; storage can be blocked, so
// every access is best-effort and dark is the fallback.
const themeListeners = new Set<() => void>()
let themeFallback: 'dark' | 'light' = 'dark'

function subscribeToTheme(onChange: () => void) {
  themeListeners.add(onChange)
  return () => themeListeners.delete(onChange)
}

function readTheme(): 'dark' | 'light' {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY) === 'light' ? 'light' : 'dark'
  } catch {
    return themeFallback
  }
}

function writeTheme(next: 'dark' | 'light') {
  themeFallback = next
  try {
    localStorage.setItem(THEME_STORAGE_KEY, next)
  } catch {}
  themeListeners.forEach((listener) => listener())
}

/**
 * Which items have been read.
 *
 * Kept in the browser, not on a server: the dashboard has no accounts and the
 * Supabase path is not wired up, so "read" is one person's state on one
 * machine. localStorage is an external store, so it is read through
 * useSyncExternalStore — React then renders the server's empty snapshot and
 * swaps in the stored one after hydration, with no mismatch.
 */
const readListeners = new Set<() => void>()

function subscribeToReadItems(onChange: () => void) {
  readListeners.add(onChange)
  window.addEventListener('storage', onChange)
  return () => {
    readListeners.delete(onChange)
    window.removeEventListener('storage', onChange)
  }
}

function readItemsSnapshot(): string {
  try {
    return window.localStorage.getItem(READ_STORAGE_KEY) || ''
  } catch {
    // Blocked storage (private window, disabled cookies): nothing is read.
    return ''
  }
}

function serverReadItemsSnapshot(): string {
  return ''
}

function persistReadItems(ids: string[]) {
  try {
    if (ids.length) window.localStorage.setItem(READ_STORAGE_KEY, JSON.stringify(ids))
    else window.localStorage.removeItem(READ_STORAGE_KEY)
  } catch {
    // Ignore: the page still works, the state just will not survive a reload.
  }
  readListeners.forEach((listener) => listener())
}

function useReadItems() {
  const raw = useSyncExternalStore(subscribeToReadItems, readItemsSnapshot, serverReadItemsSnapshot)

  const readIds = useMemo(() => {
    if (!raw) return new Set<string>()
    try {
      return new Set<string>(JSON.parse(raw) as string[])
    } catch {
      return new Set<string>()
    }
  }, [raw])

  const toggle = (id: string) => {
    const next = new Set(readIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    persistReadItems([...next])
  }

  const clear = () => persistReadItems([])

  return { readIds, toggle, clear }
}

export default function Dashboard({
  items: digestItems,
  sources: digestSources,
  topics: digestTopics,
  generatedAt: digestGeneratedAt,
  glossary,
  hosted = false,
  week,
}: {
  items: DigestItem[]
  sources: DigestSource[]
  topics: string[]
  generatedAt: string
  glossary: GlossaryEntry[]
  // On Vercel for other readers: the owner-only sections are left out.
  hosted?: boolean
  // Set when showing a past week from the archive: its Monday, YYYY-MM-DD.
  week?: string
}) {
  const { readIds, toggle: toggleRead, clear: clearRead } = useReadItems()

  const [query, setQuery] = useState('')
  const [selectedFlag, setSelectedFlag] = useState<Flag | null>(null)
  const [selectedSource, setSelectedSource] = useState<string | null>(null)
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null)
  const [groupBy, setGroupBy] = useState<Record<'topic' | 'flag', boolean>>({
    topic: true,
    flag: true,
  })
  const [format, setFormat] = useState<Format>('zip')
  const [depth, setDepth] = useState<Depth>('brief')
  const [copied, setCopied] = useState<'idle' | 'copied' | 'failed'>('idle')
  /*
   * What the download leaves out, one set per dimension.
   *
   * These were once a set of combinations — a chip per file — which repeated
   * "Super & tax" three times and "ACT" seven, fifteen chips to say what ten
   * can. Urgency and category are independent, so they are chosen
   * independently and applied together.
   *
   * Held as what is excluded rather than what is kept, so a category that
   * appears when you change a filter is included by default rather than
   * silently missing from the download.
   */
  const [excludedFlags, setExcludedFlags] = useState<Set<string>>(new Set())
  const [excludedTopics, setExcludedTopics] = useState<Set<string>>(new Set())
  const [paywallOpen, setPaywallOpen] = useState(false)
  const [selectedExactness, setSelectedExactness] = useState<Exactness>('all')
  const [dateRange, setDateRange] = useState<DateRange>('all')
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [hideRead, setHideRead] = useState(false)

  const [status, setStatus] = useState<Status | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)

  // Light or dark, remembered in this browser. The class on <html> flips the
  // palette in globals.css; storage can be blocked, so it is best-effort.
  const theme = useSyncExternalStore(subscribeToTheme, readTheme, () => 'dark' as const)
  useEffect(() => {
    document.documentElement.classList.toggle('light', theme === 'light')
  }, [theme])
  const toggleTheme = () => writeTheme(theme === 'light' ? 'dark' : 'light')

  // Captured once per mount: calling Date.now() while rendering makes the
  // filter's result depend on when React happened to re-render.
  const [mountedAt] = useState(() => Date.now())

  const [telegramLoading, setTelegramLoading] = useState(false)
  const [telegramMessage, setTelegramMessage] = useState('')
  const [telegramPreview, setTelegramPreview] = useState('')

  useEffect(() => {
    fetch('/api/status')
      .then((response) => response.json())
      .then(setStatus)
      .catch(() => setStatus(null))
  }, [])

  const sources = useMemo(
    () => Array.from(new Set(digestItems.map((item) => item.source_name))).sort(),
    [digestItems]
  )

  // Everything except the single-day filter. The timeline is built from these,
  // so a selected day never hides the other days you could switch to.
  const timelineItems = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const cutoff =
      dateRange === 'all'
        ? null
        : new Date(mountedAt - (dateRange === 'week' ? 7 : 30) * 24 * 60 * 60 * 1000)

    return digestItems.filter((item) => {
      if (selectedFlag && item.flag !== selectedFlag) return false
      if (selectedSource && item.source_name !== selectedSource) return false
      if (selectedTopic && item.topic !== selectedTopic) return false
      if (selectedExactness !== 'all' && (item.link_exactness || 'broad') !== selectedExactness) return false
      if (cutoff && new Date(item.created_at) < cutoff) return false
      if (hideRead && readIds.has(item.id)) return false
      if (needle) {
        const haystack = `${item.title} ${item.teaser} ${item.source_name} ${item.topic}`.toLowerCase()
        if (!haystack.includes(needle)) return false
      }
      return true
    })
  }, [digestItems, query, selectedFlag, selectedSource, selectedTopic, selectedExactness, dateRange, hideRead, readIds, mountedAt])

  const filteredItems = useMemo(
    () =>
      selectedDate
        ? timelineItems.filter((item) => toDayKey(item.created_at) === selectedDate)
        : timelineItems,
    [timelineItems, selectedDate]
  )

  const stats = useMemo(() => {
    const count = (flag: Flag) => digestItems.filter((item) => item.flag === flag).length
    return {
      total: digestItems.length,
      unread: digestItems.filter((item) => !readIds.has(item.id)).length,
      act: count('ACT'),
      know: count('KNOW'),
      note: count('NOTE'),
      unreadAct: digestItems.filter((item) => item.flag === 'ACT' && !readIds.has(item.id)).length,
    }
  }, [digestItems, readIds])

  const itemsByTopic = useMemo(() => {
    const grouped = new Map<string, DigestItem[]>()
    filteredItems.forEach((item) => {
      if (!grouped.has(item.topic)) grouped.set(item.topic, [])
      grouped.get(item.topic)!.push(item)
    })
    return grouped
  }, [filteredItems])

  // Offered in the order the monitor classified them, but only the ones this
  // digest actually has: a category with no news this week is not a filter
  // worth clicking.
  const topics = useMemo(() => {
    const present = new Set(digestItems.map((item) => item.topic))
    return digestTopics.filter((topic) => present.has(topic))
  }, [digestItems, digestTopics])

  // Category first when both are ticked, so a file reads compliance-act.md.
  const grouping = useMemo(
    () =>
      DIMENSIONS.filter((dimension) => groupBy[dimension.key]).map(
        (dimension) => dimension.key
      ) as Grouping,
    [groupBy]
  )

  // Which urgencies and categories this week's items actually have, in the
  // order they are ranked and classified.
  const flagsPresent = useMemo(
    () => (Object.keys(flagMeta) as Flag[]).filter((flag) => filteredItems.some((i) => i.flag === flag)),
    [filteredItems]
  )

  const topicsPresent = useMemo(
    () => digestTopics.filter((topic) => filteredItems.some((i) => (i.topic || FALLBACK_TOPIC) === topic)),
    [filteredItems, digestTopics]
  )

  const keptFlags = flagsPresent.filter((flag) => !excludedFlags.has(flag))
  const keptTopics = topicsPresent.filter((topic) => !excludedTopics.has(topic))

  // The two choices narrow together: KNOW plus Super & tax is the KNOW items
  // on tax, not everything KNOW and everything on tax.
  const downloadItems = useMemo(
    () =>
      filteredItems.filter(
        (item) =>
          !excludedFlags.has(item.flag) && !excludedTopics.has(item.topic || FALLBACK_TOPIC)
      ),
    [filteredItems, excludedFlags, excludedTopics]
  )

  const chosenDepth = DEPTHS.find((option) => option.value === depth) || DEPTHS[0]

  const briefingFiles = useMemo(
    () =>
      chosenDepth.prompt === null
        ? buildReadingFiles(downloadItems, grouping, digestTopics, summaryOrigin)
        : buildBriefingFiles(
            downloadItems,
            grouping,
            digestTopics,
            chosenDepth.chunk,
            chosenDepth.prompt
          ),
    [downloadItems, grouping, digestTopics, chosenDepth]
  )

  const briefing = useMemo(
    () => combineBriefing(briefingFiles, downloadItems.filter((item) => !item.ref).length),
    [briefingFiles, downloadItems]
  )

  const biggestFile = useMemo(
    () => [...briefingFiles].sort((a, b) => b.items - a.items)[0],
    [briefingFiles]
  )

  /*
   * What a chip would contribute if it were ticked, given the other row.
   *
   * So with KNOW ticked on its own, Compliance reads the number of KNOW items
   * in Compliance rather than its total — and the number does not change when
   * you tick the chip itself, which would make it look like the count was
   * reacting to the wrong thing.
   */
  const countForFlag = (flag: string) =>
    filteredItems.filter(
      (item) => item.flag === flag && !excludedTopics.has(item.topic || FALLBACK_TOPIC)
    ).length

  const countForTopic = (topic: string) =>
    filteredItems.filter(
      (item) => (item.topic || FALLBACK_TOPIC) === topic && !excludedFlags.has(item.flag)
    ).length

  const toggleIn = (set: Set<string>, value: string) => {
    const next = new Set(set)
    if (next.has(value)) next.delete(value)
    else next.add(value)
    return next
  }

  /**
   * Save the briefing for whatever the filters currently show.
   *
   * Built in the browser from the digest already loaded, so downloading costs
   * no request and reaches no publisher. Either shape holds each item's title,
   * teaser and link and nothing else — the same fields the feed handed over.
   */
  /**
   * Put the briefing on the clipboard instead of on disk.
   *
   * The shortest route into an AI window: no file to find, and no format for a
   * chat app to refuse — .zip in particular is not accepted as an upload.
   *
   * navigator.clipboard.writeText can sit unresolved rather than rejecting
   * when the page does not have focus, which left the button saying "Copy"
   * with no way to tell whether anything had happened. So the promise is
   * raced against a timeout and the old textarea route is the fallback, and
   * the button reports either outcome rather than only the happy one.
   */
  const copyBriefing = async () => {
    const viaTextarea = () => {
      const area = document.createElement('textarea')
      area.value = briefing.text
      area.style.position = 'fixed'
      area.style.opacity = '0'
      document.body.appendChild(area)
      area.select()
      const ok = document.execCommand('copy')
      area.remove()
      return ok
    }

    let ok = false
    try {
      await Promise.race([
        navigator.clipboard.writeText(briefing.text),
        new Promise((_, reject) => window.setTimeout(() => reject(new Error('timeout')), 1000)),
      ])
      ok = true
    } catch {
      ok = viaTextarea()
    }

    setCopied(ok ? 'copied' : 'failed')
    window.setTimeout(() => setCopied('idle'), 2500)
  }

  const downloadBriefing = () => {
    const zipped = format === 'zip'
    // Unzipping used to give a handful of Markdown files with no entry point.
    // README.md says where they came from and what to do with them; links.md
    // is every item once, to open by hand. IMPROVEMENTS.md item 12.
    const zipEntries = [
      {
        name: 'README.md',
        text:
          chosenDepth.prompt === null
            ? `# Summaries — ${(digestGeneratedAt || '').slice(0, 10)}\n\nOne file per group. Each item carries its summary, who wrote it, and its link. An ACT item is read at its source before it is acted on.\n`
            : bundleReadme(briefingFiles, digestGeneratedAt),
      },
      { name: 'links.md', text: bundleLinks(downloadItems, digestGeneratedAt) },
      ...briefingFiles,
    ]
    const blob = zipped
      ? new Blob([buildZip(zipEntries, new Date(digestGeneratedAt || Date.now()))], {
          type: 'application/zip',
        })
      : new Blob([briefing.text], { type: 'text/markdown;charset=utf-8' })

    // One group on its own is named after that group, so a download of just
    // Super & tax · KNOW arrives as super-tax-know-2026-09-14.md.
    const day = (digestGeneratedAt || new Date().toISOString()).slice(0, 10)
    const name =
      briefingFiles.length === 1 && grouping.length
        ? `${slug(briefingFiles[0].label)}-${day}.${format}`
        : briefingFilename(grouping, digestGeneratedAt, format)

    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = name
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  }

  // The Bibliography as a file: every article, grouped by publisher, linked.
  const downloadSourceLinks = () => {
    const blob = new Blob([bundleLinksBySource(digestItems, digestGeneratedAt)], {
      type: 'text/markdown;charset=utf-8',
    })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `links-by-source-${(digestGeneratedAt || new Date().toISOString()).slice(0, 10)}.md`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  }

  const filtersActive =
    Boolean(query || selectedFlag || selectedSource || selectedTopic || selectedDate || hideRead) ||
    selectedExactness !== 'all' ||
    dateRange !== 'all'

  const resetFilters = () => {
    setQuery('')
    setSelectedFlag(null)
    setSelectedSource(null)
    setSelectedTopic(null)
    setSelectedExactness('all')
    setDateRange('all')
    setSelectedDate(null)
    setHideRead(false)
  }

  // The recipient is TELEGRAM_CHAT_ID on the server and is deliberately not
  // sent from here — see the comment in app/api/telegram/send/route.ts.
  const handleTelegramSend = async () => {
    setTelegramLoading(true)
    setTelegramMessage('')
    setTelegramPreview('')

    try {
      const response = await fetch('/api/telegram/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selectedFlag }),
      })
      const data = await response.json()

      if (data.success) {
        if (!data.sent) {
          setTelegramMessage(
            'Telegram is not set up here, so nothing was sent. This is the exact message it would send:'
          )
          setTelegramPreview(data.preview || '')
        } else {
          setTelegramMessage('✓ Sent to your Telegram chat')
        }
      } else {
        setTelegramMessage(data.error || 'Failed to send')
      }
    } catch {
      setTelegramMessage('Could not reach /api/telegram/send')
    } finally {
      setTelegramLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100">
      <div className="mx-auto max-w-5xl">
        <header className="mb-10 rounded-3xl border border-slate-800 bg-slate-900/60 p-8 shadow-2xl">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-sky-300">Industry Update Monitor</p>
              <h1 className="mt-4 text-4xl font-bold tracking-tight text-white">
                {week
                  ? `Week of ${new Date(`${week}T00:00:00`).toLocaleDateString('en-AU', { day: 'numeric', month: 'long', year: 'numeric' })}`
                  : 'This week in Australian advice'}
              </h1>
              <p className="mt-4 max-w-3xl text-base leading-7 text-slate-300">
                A weekly round-up of the Australian financial advice trade press and regulators, sorted by urgency
                and topic. Every story comes from a free public source. The dot points are written by an AI model
                from the publisher&apos;s own text, and every story links to the original. Tap a box to read it.
              </p>
              <p className="mt-3 text-sm text-slate-400">
                Updated {formatDay(digestGeneratedAt)} · {digestItems.length} stories from {digestSources.length}{' '}
                publications
              </p>
              <p className="mt-3 flex gap-4 text-sm">
                {week ? (
                  <Link href="/" className="text-sky-300 hover:underline">
                    ← This week
                  </Link>
                ) : null}
                <Link href="/archive" className="text-sky-300 hover:underline">
                  📚 Past weeks
                </Link>
              </p>
            </div>
            <div className="flex gap-2">
            <button
              onClick={toggleTheme}
              className="rounded-lg bg-slate-800 px-4 py-2 text-white hover:bg-slate-700"
              title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            >
              {theme === 'light' ? '☾' : '☀'}
            </button>
            {hosted ? null : (
            <button
              onClick={() => setSettingsOpen(true)}
              className="rounded-lg bg-slate-800 px-4 py-2 text-white hover:bg-slate-700"
              title="Settings"
            >
              ⚙️
            </button>
            )}
            </div>
          </div>
        </header>

        <section className="grid gap-6 md:grid-cols-4">
          {[
            { label: 'Total', value: stats.total },
            { label: 'Unread', value: stats.unread },
            { label: '🔴 Act now', value: stats.act },
            { label: '🟠 Worth knowing', value: stats.know },
          ].map((card) => (
            <div key={card.label} className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <div className="text-sm uppercase tracking-[0.2em] text-slate-400">{card.label}</div>
              <div className="mt-3 text-3xl font-bold text-white">{card.value}</div>
            </div>
          ))}
        </section>

        <CategoryBoard
          items={digestItems}
          glossary={glossary}
          readIds={readIds}
          onToggleRead={toggleRead}
          generatedAt={digestGeneratedAt}
        />

        <section className="mt-10 rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
          <div className="mb-6 flex flex-col gap-4">
            <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
              <h2 className="text-2xl font-semibold text-white">All stories</h2>
              <div className="text-sm text-slate-400">
                Showing {filteredItems.length} of {digestItems.length}
                {filtersActive ? (
                  <button
                    onClick={resetFilters}
                    className="ml-3 rounded-full border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-300 hover:border-slate-500"
                  >
                    Clear filters
                  </button>
                ) : null}
              </div>
            </div>

            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search titles, teasers, sources and topics…"
              className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
            />

            <div className="flex flex-wrap gap-3">
              <select
                value={selectedSource || ''}
                onChange={(event) => setSelectedSource(event.target.value || null)}
                className="rounded-full border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:border-slate-600"
              >
                <option value="">All sources</option>
                {sources.map((source) => (
                  <option key={source} value={source}>
                    {source}
                  </option>
                ))}
              </select>

              <select
                value={selectedTopic || ''}
                onChange={(event) => setSelectedTopic(event.target.value || null)}
                className="rounded-full border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:border-slate-600"
              >
                <option value="">All categories</option>
                {topics.map((topic) => (
                  <option key={topic} value={topic}>
                    {topic}
                  </option>
                ))}
              </select>

              <select
                value={dateRange}
                onChange={(event) => setDateRange(event.target.value as DateRange)}
                className="rounded-full border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:border-slate-600"
              >
                <option value="all">Any date</option>
                <option value="week">Last 7 days</option>
                <option value="month">Last 30 days</option>
              </select>

              <select
                value={selectedExactness}
                onChange={(event) => setSelectedExactness(event.target.value as Exactness)}
                className="rounded-full border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:border-slate-600"
              >
                <option value="all">Any link</option>
                <option value="exact">Article links only</option>
                <option value="fallback">Section pages</option>
                <option value="broad">Manual review</option>
              </select>

              <div className="flex gap-2">
                {(Object.keys(flagMeta) as Flag[]).map((flag) => (
                  <button
                    key={flag}
                    onClick={() => setSelectedFlag(selectedFlag === flag ? null : flag)}
                    className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.1em] transition-all ${
                      selectedFlag === flag
                        ? flagMeta[flag].button
                        : 'border border-slate-700 bg-slate-800 text-slate-300 hover:border-slate-600'
                    }`}
                  >
                    {flag}
                  </button>
                ))}
              </div>

              <label className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-300">
                <input
                  type="checkbox"
                  checked={hideRead}
                  onChange={(event) => setHideRead(event.target.checked)}
                  className="h-4 w-4 accent-sky-500"
                />
                Hide stories I&apos;ve read
              </label>

              {readIds.size > 0 ? (
                <button
                  onClick={clearRead}
                  className="rounded-full border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:border-slate-500"
                >
                  Mark all unread ({readIds.size})
                </button>
              ) : null}
            </div>

            {selectedDate ? (
              <div className="text-xs text-slate-400">
                Filtered to {formatDay(selectedDate)} — click the day again in the timeline to clear it.
              </div>
            ) : null}
          </div>

          <div className="mb-6 text-xs text-slate-400">
            &quot;Article links only&quot; keeps items whose link points at the story itself. Section pages and
            manual-review items are follow-ups to open by hand, not verified article links.
          </div>

          {hosted ? null : (
          <details className="mb-8 rounded-2xl border border-sky-900/60 bg-sky-950/30 p-5">
            <summary className="cursor-pointer text-sm font-semibold text-slate-300">
              Advanced: export stories to paste into an AI chat
            </summary>
            <div className="mt-4 flex flex-col gap-4">
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="text-base font-semibold text-white">Download for summarising</h3>
                  <button
                    onClick={() => setPaywallOpen(true)}
                    className="rounded-full border border-emerald-700/60 bg-emerald-950/40 px-3 py-1 text-[11px] font-semibold text-emerald-300 hover:border-emerald-500"
                  >
                    ⓘ Never scrapes paid sources
                  </button>
                </div>
                <p className="mt-1 max-w-3xl text-xs text-slate-400">
                  Paste-ready blocks carrying the summarising prompt and each item&apos;s own words
                  — the headline, and whatever the publisher put in their public feed. Nothing is
                  fetched from an article page. Paste a block into your own AI tool, save the reply,
                  and merge it back with{' '}
                  <code className="rounded bg-slate-800 px-1 py-0.5 text-[11px] text-slate-300">
                    python src/monitor.py --import-summaries output/reply.md
                  </code>
                  .
                </p>
              </div>

              <div className="flex flex-wrap items-end gap-3">
                <div className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                  Split files by
                  <div className="flex gap-2">
                    {DIMENSIONS.map((dimension) => (
                      <label
                        key={dimension.key}
                        title={dimension.example}
                        className={`flex cursor-pointer items-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold normal-case tracking-normal transition-colors ${
                          groupBy[dimension.key]
                            ? 'border-sky-500 bg-sky-600/20 text-white'
                            : 'border-slate-700 bg-slate-800 text-slate-400 hover:border-slate-600'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={groupBy[dimension.key]}
                          onChange={(event) =>
                            setGroupBy((current) => ({
                              ...current,
                              [dimension.key]: event.target.checked,
                            }))
                          }
                          className="h-4 w-4 accent-sky-500"
                        />
                        {dimension.label}
                      </label>
                    ))}
                  </div>
                </div>

                <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                  Detail
                  <select
                    value={depth}
                    onChange={(event) => setDepth(event.target.value as Depth)}
                    className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold normal-case tracking-normal text-white hover:border-slate-600"
                  >
                    {DEPTHS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                  Download as
                  <select
                    value={format}
                    onChange={(event) => setFormat(event.target.value as Format)}
                    className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold normal-case tracking-normal text-white hover:border-slate-600"
                  >
                    {FORMATS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="flex gap-2">
                  {/*
                    Copy first: pasting straight into a chat has no file for an
                    AI app to refuse, and .zip in particular is not accepted as
                    an upload by Claude or ChatGPT.
                  */}
                  <button
                    onClick={copyBriefing}
                    disabled={briefing.pastes === 0}
                    className={`rounded-xl border px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:border-slate-800 disabled:bg-transparent disabled:text-slate-600 ${
                      copied === 'failed'
                        ? 'border-amber-600/60 bg-amber-600/15 text-amber-200'
                        : 'border-sky-600/60 bg-sky-600/15 text-sky-200 hover:bg-sky-600/25'
                    }`}
                  >
                    {copied === 'copied' ? '✓ Copied' : copied === 'failed' ? 'Copy failed' : 'Copy'}
                  </button>
                  <button
                    onClick={downloadBriefing}
                    disabled={briefing.pastes === 0}
                    className="rounded-xl bg-sky-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-sky-500 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
                  >
                    Download
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-4 border-t border-slate-800/80 pt-3 text-xs">
              {/*
                The count, and — when nothing is selected — why. This used to
                wrap the file picker too, so unticking every file hid the
                picker and left no way back except changing a filter.
              */}
              {keptFlags.length === 0 || keptTopics.length === 0 ? (
                <span className="font-semibold text-amber-400">
                  {keptFlags.length === 0
                    ? 'No urgency selected — tick ACT, KNOW or NOTE below.'
                    : 'No category selected — tick at least one below.'}
                </span>
              ) : briefingFiles.length === 0 ? (
                <span className="text-slate-500">
                  Nothing to download — widen the filters above.
                </span>
              ) : (
                <span className="font-semibold text-slate-300">
                  {format === 'zip'
                    ? `${briefingFiles.length} file${briefingFiles.length === 1 ? '' : 's'}`
                    : `1 file, ${briefing.pastes} paste${briefing.pastes === 1 ? '' : 's'}`}
                  {' · '}
                  {briefing.items} item{briefing.items === 1 ? '' : 's'}
                  {format === 'zip' && biggestFile && grouping.length
                    ? ` · biggest is ${biggestFile.label}, ${biggestFile.items} items`
                    : ''}
                </span>
              )}

              {/*
                Two rows, not one chip per combination. Urgency and category
                are independent, so they are picked independently and applied
                together: KNOW plus Super & tax is the KNOW items on tax.
              */}
              <div className="mt-3 space-y-2">
                {[
                  {
                    key: 'flag',
                    label: 'Urgency',
                    values: flagsPresent as string[],
                    excluded: excludedFlags,
                    setExcluded: setExcludedFlags,
                    count: countForFlag,
                  },
                  {
                    key: 'topic',
                    label: 'Category',
                    values: topicsPresent,
                    excluded: excludedTopics,
                    setExcluded: setExcludedTopics,
                    count: countForTopic,
                  },
                ].map((row) =>
                  row.values.length === 0 ? null : (
                    <div key={row.key} className="flex flex-wrap items-center gap-1.5">
                      <span className="w-16 shrink-0 text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-500">
                        {row.label}
                      </span>
                      {row.values.map((value) => {
                        const included = !row.excluded.has(value)
                        const count = row.count(value)
                        return (
                          <button
                            key={value}
                            onClick={() => row.setExcluded(toggleIn(row.excluded, value))}
                            aria-pressed={included}
                            title={
                              included && count === 0
                                ? 'Nothing here with the other row’s choice, so no file'
                                : undefined
                            }
                            // A ticked chip with nothing in it is muted rather
                            // than bright: it is still on, but it will not
                            // produce a file, and bright blue implied it would.
                            className={`rounded-lg border px-2.5 py-1 text-[11px] font-medium transition-colors ${
                              !included
                                ? 'border-slate-800 bg-slate-900/60 text-slate-500 hover:border-slate-700'
                                : count === 0
                                  ? 'border-slate-700 bg-slate-800/40 text-slate-500'
                                  : 'border-sky-600/60 bg-sky-600/15 text-sky-200'
                            }`}
                          >
                            <span className="mr-1">{included ? '✓' : '+'}</span>
                            {value}{' '}
                            <span
                              className={included && count > 0 ? 'text-sky-400/70' : 'text-slate-600'}
                            >
                              ({count})
                            </span>
                          </button>
                        )
                      })}
                      {row.excluded.size > 0 ? (
                        <button
                          onClick={() => row.setExcluded(new Set())}
                          className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-400 hover:border-slate-500"
                        >
                          All
                        </button>
                      ) : null}
                    </div>
                  )
                )}
              </div>

              {grouping.length > 0 && briefingFiles.length > 0 ? (
                <div className="mt-2 text-[11px] text-slate-600">
                  {briefingFiles.map((file) => file.name).join('   ')}
                </div>
              ) : null}

              <div className="mt-2 text-[11px] text-slate-500">
                {copied === 'failed'
                  ? 'The browser refused the clipboard — use Download instead, or click the page once and retry.'
                  : format === 'zip'
                    ? 'Unzip first — Claude and ChatGPT do not accept .zip uploads. Upload the .md files, or use Copy to paste one straight in.'
                    : 'Upload the .md file to Claude or ChatGPT, or use Copy to paste it straight in.'}
              </div>

              {briefing.skipped > 0 ? (
                <div className="mt-2 text-amber-500/80">
                  {briefing.skipped} item{briefing.skipped === 1 ? '' : 's'} left out — no ID to
                  match a reply back to.
                </div>
              ) : null}
            </div>
          </details>
          )}

          <UnreachableSources />

          <div className="space-y-8">
            {itemsByTopic.size === 0 ? (
              <div className="rounded-2xl border border-slate-700 bg-slate-800/30 p-6 text-center text-slate-400">
                Nothing matches these filters.
              </div>
            ) : null}

            {Array.from(itemsByTopic.entries()).map(([topic, items]) => (
              <div key={topic}>
                <h3 className="mb-4 text-lg font-semibold text-slate-300">
                  {topic} <span className="text-slate-500">({items.length})</span>
                </h3>
                <div className="space-y-4">
                  {items.map((item) => {
                    const isRead = readIds.has(item.id)
                    // A newsletter's link resolves only in your own mailbox,
                    // so the link-exactness badge would say "section page" and
                    // mean nothing. Say what it actually is.
                    const linkMeta =
                      item.intake === 'email'
                        ? { label: 'Newsletter', className: 'border-sky-500/40 bg-sky-500/10 text-sky-300' }
                        : exactnessMeta[(item.link_exactness || 'broad') as keyof typeof exactnessMeta]

                    return (
                      <article
                        key={item.id}
                        className={`rounded-2xl border border-slate-800 bg-slate-950/70 p-5 transition-opacity ${
                          isRead ? 'opacity-50' : ''
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <span
                              className={`rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${flagMeta[item.flag].chip}`}
                            >
                              {item.flag}
                            </span>
                            {typeof item.confidence === 'number' ? (
                              <span className="text-xs text-slate-400">
                                {Math.round(item.confidence * 100)}% confidence
                              </span>
                            ) : null}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-slate-400">
                            <span>{item.source_name}</span>
                            <span className={`rounded-full border px-2 py-0.5 uppercase tracking-[0.12em] ${linkMeta.className}`}>
                              {linkMeta.label}
                            </span>
                          </div>
                        </div>

                        <h3 className={`mt-4 text-xl font-semibold ${isRead ? 'text-slate-400 line-through' : 'text-white'}`}>
                          {item.title}
                        </h3>
                        <p className="mt-2 text-sm leading-6 text-slate-300">{item.teaser}</p>
                        <div className="mt-3 text-xs text-slate-400">{formatDay(item.created_at)}</div>

                        {item.ai_summary ? (
                          <div className="mt-3 rounded-xl border border-slate-700 bg-slate-900 p-3">
                            <div className="mb-1 text-xs uppercase tracking-[0.15em] text-slate-400">
                              {`${summaryOrigin(item.ai_source)}${
                                item.ai_generated_at ? ` · ${formatDay(item.ai_generated_at)}` : ''
                              }`}
                            </div>
                            <ul className="list-disc space-y-1 pl-5 text-sm leading-6 text-slate-200">
                              {summaryPoints(item.ai_summary).map((point, index) => (
                                <li key={index}>
                                  {boldRuns(point).map((run, runIndex) =>
                                    run.bold ? (
                                      <strong key={runIndex} className="font-semibold text-white">
                                        {run.text}
                                      </strong>
                                    ) : (
                                      <span key={runIndex}>{run.text}</span>
                                    )
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : null}

                        <div className="mt-4 flex items-center gap-4">
                          <a
                            href={item.link}
                            target="_blank"
                            rel="noreferrer"
                            className="text-sm font-medium text-sky-300 underline underline-offset-4"
                          >
                            {item.intake === 'email' ? 'Open in Gmail' : 'Read at source'}
                          </a>
                          <label className="flex items-center gap-2 text-sm text-slate-400">
                            <input
                              type="checkbox"
                              checked={isRead}
                              onChange={() => toggleRead(item.id)}
                              className="h-4 w-4 accent-sky-500"
                            />
                            Read
                          </label>
                        </div>
                      </article>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-10">
          <Calendar
            items={timelineItems}
            selectedDate={selectedDate}
            onDateSelect={(date) => setSelectedDate(date || null)}
            glossary={glossary}
            readIds={readIds}
            onToggleRead={toggleRead}
          />
        </section>

        {hosted ? null : (
        <>
        <section className="mt-10 grid gap-6 lg:grid-cols-3">
          <IntegrationCard
            title="Email digest"
            status={status?.email}
            action={
              <a
                href="/api/email/preview"
                target="_blank"
                rel="noreferrer"
                className="inline-block rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
              >
                Preview the email
              </a>
            }
          />
          <IntegrationCard title="Telegram" status={status?.telegram} />
          <IntegrationCard title="AI summariser" status={status?.ai} />
        </section>

        <section id="telegram-scroll" className="mt-10 rounded-3xl border border-slate-800 bg-slate-900 p-8">
          <h2 className="text-2xl font-semibold text-white">✈️ Send this week to Telegram</h2>
          <p className="mt-2 text-sm text-slate-400">
            Sends the same message as the Monday run to your own Telegram chat: the headlines, Act now first, each
            with its first dot point. If you have picked an urgency in the filters above, only that urgency is sent.
            Telegram is free. If it is not set up yet, nothing is sent and you see the message instead.
          </p>
          <p className="mt-2 text-sm text-slate-400">
            It only ever goes to your own chat (<code className="text-slate-300">TELEGRAM_CHAT_ID</code>). There is
            no box to type another recipient, on purpose, so nobody who finds this page can use it to message others.
          </p>
          <div className="mt-6 space-y-4">
            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                onClick={handleTelegramSend}
                disabled={telegramLoading}
                className="rounded-lg bg-sky-600 px-6 py-2 font-medium text-white hover:bg-sky-700 disabled:opacity-50"
              >
                {telegramLoading ? 'Working…' : status?.telegram.configured ? 'Send' : 'Preview message'}
              </button>
            </div>
            {telegramMessage ? (
              <div
                className={`rounded-lg px-4 py-3 text-sm ${
                  telegramMessage.startsWith('✓')
                    ? 'bg-green-500/10 text-green-300'
                    : telegramPreview
                      ? 'bg-slate-800 text-slate-300'
                      : 'bg-red-500/10 text-red-300'
                }`}
              >
                {telegramMessage}
              </div>
            ) : null}
            {telegramPreview ? (
              <>
                <p className="text-xs text-slate-500">
                  Shown as raw text: the &lt;b&gt; and &lt;i&gt; tags become bold and italics in Telegram.
                </p>
                <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-xl border border-slate-700 bg-slate-950 p-4 text-xs leading-5 text-slate-300">
                  {telegramPreview}
                </pre>
              </>
            ) : null}
          </div>
        </section>

        </>
        )}

        <section className="mt-10 rounded-3xl border border-slate-800 bg-slate-900 p-8">
          <h2 className="text-2xl font-semibold text-white">How it works</h2>
          <ul className="mt-6 space-y-3 text-slate-300">
            <li>• Only free, public news feeds from the trade press and regulators. Nothing behind a paywall.</li>
            <li>
              • Each story is sorted by urgency (🔴 Act now, 🟠 Worth knowing, 🟢 Background) and by topic, using
              keyword rules. Read the source before relying on a call.
            </li>
            <li>• The dot points are written by an AI model and labelled as such. They can be wrong; the source is one tap away.</li>
            <li>• Dotted words are explained from a hand-written glossary.</li>
          </ul>
          <p className="mt-6 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm leading-6 text-amber-200">
            General information only, not financial advice. It does not take into account anyone&apos;s objectives,
            financial situation or needs. Summaries are produced automatically and may contain errors; check the
            original source before acting on anything here.
          </p>
        </section>

        <section className="mt-10 rounded-3xl border border-slate-800 bg-slate-900 p-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-2xl font-semibold text-white">Bibliography</h2>
            <button
              onClick={downloadSourceLinks}
              className="rounded-xl border border-sky-600/60 bg-sky-600/15 px-4 py-2 text-sm font-semibold text-sky-200 hover:bg-sky-600/25"
            >
              Download all links
            </button>
          </div>
          <p className="mt-2 text-sm text-slate-400">
            Publications this digest drew on — every article, with its own link
          </p>
          <div className="mt-6 space-y-2">
            {digestSources.map((source) => (
              <div key={source.name} className="rounded-xl border border-slate-700 bg-slate-800/50 px-4 py-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-white">{source.name}</div>
                  <div className="text-xs text-slate-500">
                    {source.count} item{source.count !== 1 ? 's' : ''} in this digest
                  </div>
                </div>
                {source.home ? (
                  <a
                    href={source.home}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-medium text-slate-400 underline underline-offset-2 hover:text-slate-200"
                  >
                    Publisher&apos;s website
                  </a>
                ) : null}
              </div>
              {/* The articles this publisher contributed, each linked to its
                  own page — the home page alone does not say what was read. */}
              <ul className="mt-3 border-t border-slate-700 pt-2">
                {digestItems
                  .filter((item) => item.source_name === source.name)
                  .map((item) => (
                    <li
                      key={item.id}
                      className="flex items-center justify-between gap-4 border-b border-slate-700/60 py-1.5 text-sm last:border-b-0"
                    >
                      <span className="text-slate-300">{item.title}</span>
                      <a
                        href={item.link}
                        target="_blank"
                        rel="noreferrer"
                        className="shrink-0 rounded-lg border border-sky-600/60 bg-sky-600/15 px-3 py-1 text-xs font-semibold text-sky-300 hover:bg-sky-600/25"
                      >
                        Visit →
                      </a>
                    </li>
                  ))}
              </ul>
              </div>
            ))}
          </div>
        </section>
      </div>

      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <PaywallModal isOpen={paywallOpen} onClose={() => setPaywallOpen(false)} />
    </main>
  )
}

function IntegrationCard({
  title,
  status,
  action,
}: {
  title: string
  status?: IntegrationStatus
  action?: React.ReactNode
}) {
  const state = !status ? 'Checking…' : status.configured ? 'Configured' : 'Not configured'
  const tone = !status
    ? 'bg-slate-700 text-slate-300'
    : status.configured
      ? 'bg-emerald-500/15 text-emerald-300'
      : 'bg-slate-700/60 text-slate-300'

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex items-start justify-between gap-3">
        <div className="text-sm uppercase tracking-[0.2em] text-sky-300">{title}</div>
        <span className={`shrink-0 whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold ${tone}`}>
          {state}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-300">{status?.detail || 'Reading server configuration…'}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  )
}
