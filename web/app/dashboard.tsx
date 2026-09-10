'use client'

import { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { type DigestItem, type DigestSource, type Flag } from '@/lib/digest'
import { formatDay, toDayKey } from '@/lib/utils'
import { Calendar } from '@/components/Calendar'
import { SettingsModal } from '@/components/SettingsModal'

type Exactness = 'all' | 'exact' | 'fallback' | 'broad'
type DateRange = 'week' | 'month' | 'all'

type IntegrationStatus = { configured: boolean; detail: string }
type Status = {
  digest: { generated_at: string; items: number; sources: number }
  whatsapp: IntegrationStatus
  email: IntegrationStatus
  ai: IntegrationStatus
}

const flagMeta: Record<Flag, { blurb: string; chip: string; button: string }> = {
  ACT: {
    blurb: 'Regulatory changes, enforcement and deadlines',
    chip: 'border-red-500/40 bg-red-500/10 text-red-300',
    button: 'bg-red-600 text-white border border-red-500',
  },
  KNOW: {
    blurb: 'Policy, people and market context',
    chip: 'border-orange-500/40 bg-orange-500/10 text-orange-300',
    button: 'bg-orange-600 text-white border border-orange-500',
  },
  NOTE: {
    blurb: 'Background and reference material',
    chip: 'border-green-500/40 bg-green-500/10 text-green-300',
    button: 'bg-green-600 text-white border border-green-500',
  },
}

const exactnessMeta = {
  exact: { label: 'Exact', className: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' },
  fallback: { label: 'Section page', className: 'border-amber-500/40 bg-amber-500/10 text-amber-300' },
  broad: { label: 'Manual review', className: 'border-rose-500/40 bg-rose-500/10 text-rose-300' },
} as const

const READ_STORAGE_KEY = 'advice-monitor:read-items'

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
  generatedAt: digestGeneratedAt,
}: {
  items: DigestItem[]
  sources: DigestSource[]
  generatedAt: string
}) {
  const { readIds, toggle: toggleRead, clear: clearRead } = useReadItems()

  const [query, setQuery] = useState('')
  const [selectedFlag, setSelectedFlag] = useState<Flag | null>(null)
  const [selectedSource, setSelectedSource] = useState<string | null>(null)
  const [selectedExactness, setSelectedExactness] = useState<Exactness>('all')
  const [dateRange, setDateRange] = useState<DateRange>('all')
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [hideRead, setHideRead] = useState(false)

  const [status, setStatus] = useState<Status | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)

  // Captured once per mount: calling Date.now() while rendering makes the
  // filter's result depend on when React happened to re-render.
  const [mountedAt] = useState(() => Date.now())

  const [whatsappPhone, setWhatsappPhone] = useState('')
  const [whatsappLoading, setWhatsappLoading] = useState(false)
  const [whatsappMessage, setWhatsappMessage] = useState('')
  const [whatsappPreview, setWhatsappPreview] = useState('')

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
      if (selectedExactness !== 'all' && (item.link_exactness || 'broad') !== selectedExactness) return false
      if (cutoff && new Date(item.created_at) < cutoff) return false
      if (hideRead && readIds.has(item.id)) return false
      if (needle) {
        const haystack = `${item.title} ${item.teaser} ${item.source_name} ${item.topic}`.toLowerCase()
        if (!haystack.includes(needle)) return false
      }
      return true
    })
  }, [digestItems, query, selectedFlag, selectedSource, selectedExactness, dateRange, hideRead, readIds, mountedAt])

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

  const filtersActive =
    Boolean(query || selectedFlag || selectedSource || selectedDate || hideRead) ||
    selectedExactness !== 'all' ||
    dateRange !== 'all'

  const resetFilters = () => {
    setQuery('')
    setSelectedFlag(null)
    setSelectedSource(null)
    setSelectedExactness('all')
    setDateRange('all')
    setSelectedDate(null)
    setHideRead(false)
  }

  const handleWhatsappSend = async () => {
    if (!whatsappPhone.trim()) {
      setWhatsappMessage('Enter a WhatsApp number first, e.g. +61412345678')
      return
    }

    setWhatsappLoading(true)
    setWhatsappMessage('')
    setWhatsappPreview('')

    try {
      const response = await fetch('/api/whatsapp/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phoneNumber: whatsappPhone, selectedFlag }),
      })
      const data = await response.json()

      if (data.success) {
        if (data.demo) {
          setWhatsappMessage(
            `Twilio is not configured, so nothing was sent. This is the exact message it would send, in ${data.parts} part${data.parts === 1 ? '' : 's'}:`
          )
          setWhatsappPreview(data.preview || '')
        } else {
          setWhatsappMessage(`✓ Sent to ${whatsappPhone} in ${data.parts} part${data.parts === 1 ? '' : 's'}`)
          setWhatsappPhone('')
        }
      } else {
        setWhatsappMessage(data.error || 'Failed to send')
      }
    } catch {
      setWhatsappMessage('Could not reach /api/whatsapp/send')
    } finally {
      setWhatsappLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100">
      <div className="mx-auto max-w-5xl">
        <header className="mb-10 rounded-3xl border border-slate-800 bg-slate-900/60 p-8 shadow-2xl">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-sky-300">Industry Update Monitor</p>
              <h1 className="mt-4 text-4xl font-bold tracking-tight text-white">Digest dashboard</h1>
              <p className="mt-4 max-w-3xl text-base leading-7 text-slate-300">
                Every item below came from a public RSS feed, was flagged ACT / KNOW / NOTE by a weighted keyword
                classifier, and had its link checked. No AI, no API key, nothing behind a paywall.
              </p>
              <p className="mt-3 text-sm text-slate-400">
                Collected {formatDay(digestGeneratedAt)} · {digestItems.length} items from {digestSources.length}{' '}
                publications · refresh with <code className="text-slate-300">python src/monitor.py --json</code>
              </p>
            </div>
            <button
              onClick={() => setSettingsOpen(true)}
              className="rounded-lg bg-slate-800 px-4 py-2 text-white hover:bg-slate-700"
              title="Settings"
            >
              ⚙️
            </button>
          </div>
        </header>

        <section className="grid gap-6 md:grid-cols-4">
          {[
            { label: 'Total', value: stats.total },
            { label: 'Unread', value: stats.unread },
            { label: 'ACT', value: stats.act },
            { label: 'KNOW', value: stats.know },
          ].map((card) => (
            <div key={card.label} className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <div className="text-sm uppercase tracking-[0.2em] text-slate-400">{card.label}</div>
              <div className="mt-3 text-3xl font-bold text-white">{card.value}</div>
            </div>
          ))}
        </section>

        <section className="mt-10 grid gap-6 md:grid-cols-3">
          {(Object.keys(flagMeta) as Flag[]).map((flag) => (
            <div key={flag} className={`rounded-2xl border p-5 ${flagMeta[flag].chip}`}>
              <div className="mb-3 text-sm font-semibold uppercase tracking-[0.2em]">{flag}</div>
              <div className="text-lg font-semibold">{flagMeta[flag].blurb}</div>
            </div>
          ))}
        </section>

        <section className="mt-10 rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
          <div className="mb-6 flex flex-col gap-4">
            <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
              <h2 className="text-2xl font-semibold text-white">Latest items</h2>
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
                Hide read
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
                    const linkMeta = exactnessMeta[(item.link_exactness || 'broad') as keyof typeof exactnessMeta]

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
                              {item.ai_source === 'manual'
                                ? `Summarised by hand${
                                    item.ai_generated_at ? ` · ${formatDay(item.ai_generated_at)}` : ''
                                  }`
                                : 'Summary'}
                            </div>
                            <p className="text-sm text-slate-200">{item.ai_summary}</p>
                          </div>
                        ) : null}

                        <div className="mt-4 flex items-center gap-4">
                          <a
                            href={item.link}
                            target="_blank"
                            rel="noreferrer"
                            className="text-sm font-medium text-sky-300 underline underline-offset-4"
                          >
                            Read at source
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
          />
        </section>

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
          <IntegrationCard title="WhatsApp" status={status?.whatsapp} />
          <IntegrationCard title="AI summariser" status={status?.ai} />
        </section>

        <section id="whatsapp-scroll" className="mt-10 rounded-3xl border border-slate-800 bg-slate-900 p-8">
          <h2 className="text-2xl font-semibold text-white">📱 Send this digest to WhatsApp</h2>
          <p className="mt-2 text-sm text-slate-400">
            Sends the items currently selected by the flag filter. Without Twilio credentials nothing is sent — you get
            the exact message back to proof-read.
          </p>
          <div className="mt-6 space-y-4">
            <div className="flex flex-col gap-3 sm:flex-row">
              <input
                type="text"
                placeholder="+61412345678"
                value={whatsappPhone}
                onChange={(event) => setWhatsappPhone(event.target.value)}
                className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-white placeholder-slate-500 focus:border-green-500 focus:outline-none"
              />
              <button
                onClick={handleWhatsappSend}
                disabled={whatsappLoading}
                className="rounded-lg bg-green-600 px-6 py-2 font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {whatsappLoading ? 'Working…' : status?.whatsapp.configured ? 'Send' : 'Preview message'}
              </button>
            </div>
            {whatsappMessage ? (
              <div
                className={`rounded-lg px-4 py-3 text-sm ${
                  whatsappMessage.startsWith('✓')
                    ? 'bg-green-500/10 text-green-300'
                    : whatsappPreview
                      ? 'bg-slate-800 text-slate-300'
                      : 'bg-red-500/10 text-red-300'
                }`}
              >
                {whatsappMessage}
              </div>
            ) : null}
            {whatsappPreview ? (
              <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-xl border border-slate-700 bg-slate-950 p-4 text-xs leading-5 text-slate-300">
                {whatsappPreview}
              </pre>
            ) : null}
          </div>
        </section>

        <section className="mt-10 rounded-3xl border border-slate-800 bg-slate-900 p-8">
          <h2 className="text-2xl font-semibold text-white">How it works</h2>
          <ul className="mt-6 space-y-3 text-slate-300">
            <li>• Free-first by design: only public feeds the publisher serves to everyone.</li>
            <li>• No paywalls: nothing behind a login or subscription is fetched, stored or reconstructed.</li>
            <li>• Teasers only: the publisher&apos;s own summary, never the full article text.</li>
            <li>• Flags are weighted keywords with a confidence score — read the source before relying on a call.</li>
            <li>• Email, WhatsApp and AI stay off until you configure them; the cards above say which are live.</li>
          </ul>
        </section>

        <section className="mt-10 rounded-3xl border border-slate-800 bg-slate-900 p-8">
          <h2 className="text-2xl font-semibold text-white">Bibliography</h2>
          <p className="mt-2 text-sm text-slate-400">Publications this digest drew on</p>
          <div className="mt-6 space-y-2">
            {digestSources.map((source) => (
              <div
                key={source.name}
                className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-800/50 px-4 py-3"
              >
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
                    className="text-sm font-medium text-sky-400 underline underline-offset-2 hover:text-sky-300"
                  >
                    Visit →
                  </a>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      </div>

      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
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
