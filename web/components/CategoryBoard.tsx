'use client'

import { useEffect, useMemo, useState } from 'react'
import { boldRuns, summaryOrigin, summaryPoints, type DigestItem, type Flag } from '@/lib/digest'
import { FLAG_LABELS, FLAG_ORDER, buildBoards, unreadReason, type Board } from '@/lib/categories'
import { splitTerms, termName, type GlossaryEntry } from '@/lib/glossary'
import { formatDay } from '@/lib/utils'
import { buildSweep, saveText, sweepFilename } from '@/lib/sweep'

/**
 * The front page: one box per category, plus Act now and Read these yourself.
 * A box opens into a pop-up with every story's dot points, so the week reads
 * without opening an article or pasting anything into a chat.
 */

const FLAG_STYLE: Record<Flag, { pill: string; bar: string }> = {
  ACT: { pill: 'border-red-500/40 bg-red-500/10 text-red-300', bar: 'bg-red-500' },
  KNOW: { pill: 'border-orange-500/40 bg-orange-500/10 text-orange-300', bar: 'bg-orange-500' },
  NOTE: { pill: 'border-green-500/40 bg-green-500/10 text-green-300', bar: 'bg-green-500' },
}

function Pill({ flag, count }: { flag: Flag; count?: number }) {
  const { emoji, label } = FLAG_LABELS[flag]
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${FLAG_STYLE[flag].pill}`}
    >
      {emoji} {count === undefined ? label : `${count} ${label.toLowerCase()}`}
    </span>
  )
}

function UrgencyBar({ items }: { items: DigestItem[] }) {
  return (
    <div className="flex h-2 w-full overflow-hidden rounded-full bg-slate-800">
      {FLAG_ORDER.map((flag) => {
        const count = items.filter((item) => item.flag === flag).length
        return count ? (
          <div key={flag} className={FLAG_STYLE[flag].bar} style={{ width: `${(100 * count) / items.length}%` }} />
        ) : null
      })}
    </div>
  )
}

/** A small ⬇ that saves a group of stories as a file to share or give an AI. */
function DownloadButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation()
        onClick()
      }}
      title={`Download ${label}: headlines, dot points and links, to send a friend or an AI tool`}
      aria-label={`Download ${label}`}
      className="rounded-lg border border-slate-700 px-2 py-1 text-xs font-semibold text-slate-300 hover:border-sky-500 hover:text-sky-200"
    >
      ⬇
    </button>
  )
}

/**
 * An underlined term that shows what it means on hover or tap. The note is
 * placed against the window, not the pop-up, so it is never cut off at the
 * pop-up's edge.
 */
function Term({ text, entry }: { text: string; entry: GlossaryEntry }) {
  const [at, setAt] = useState<{ left: number; top: number; below: boolean } | null>(null)
  const show = (target: HTMLElement) => {
    const rect = target.getBoundingClientRect()
    const width = 288
    setAt({
      left: Math.max(8, Math.min(rect.left, window.innerWidth - width - 8)),
      top: rect.top > 140 ? rect.top - 8 : rect.bottom + 8,
      below: rect.top <= 140,
    })
  }
  return (
    <>
      <button
        type="button"
        onMouseEnter={(event) => show(event.currentTarget)}
        onMouseLeave={() => setAt(null)}
        onClick={(event) => (at ? setAt(null) : show(event.currentTarget))}
        onBlur={() => setAt(null)}
        className="cursor-help underline decoration-sky-400 decoration-dotted underline-offset-4"
      >
        {text}
      </button>
      {at ? (
        <span
          role="tooltip"
          style={{ left: at.left, top: at.top, transform: at.below ? undefined : 'translateY(-100%)' }}
          className="pointer-events-none fixed z-[60] block w-72 rounded-xl border border-sky-700/60 bg-slate-950 p-3 text-left text-xs font-normal leading-5 text-slate-200 shadow-xl"
        >
          <span className="block font-semibold text-sky-300">📖 {termName(entry)}</span>
          {entry.means}
        </span>
      ) : null}
    </>
  )
}

/** A dot point with its **bold** facts and its glossary terms. */
function RichText({ text, glossary }: { text: string; glossary: GlossaryEntry[] }) {
  return (
    <>
      {boldRuns(text).map((run, runIndex) => {
        const parts = splitTerms(run.text, glossary).map((part, partIndex) =>
          part.entry ? (
            <Term key={partIndex} text={part.text} entry={part.entry} />
          ) : (
            <span key={partIndex}>{part.text}</span>
          )
        )
        return run.bold ? (
          <strong key={runIndex} className="font-semibold text-white">
            {parts}
          </strong>
        ) : (
          <span key={runIndex}>{parts}</span>
        )
      })}
    </>
  )
}

function Story({
  item,
  glossary,
  isRead,
  onToggleRead,
}: {
  item: DigestItem
  glossary: GlossaryEntry[]
  isRead: boolean
  onToggleRead: () => void
}) {
  const points = summaryPoints(item.ai_summary)
  const reason = unreadReason(item)
  return (
    <article
      className={`rounded-2xl border border-slate-800 bg-slate-950/70 p-5 transition-opacity ${isRead ? 'opacity-50' : ''}`}
    >
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
        <Pill flag={item.flag} />
        <span>
          {item.source_name}
          {item.created_at ? ` · ${formatDay(item.created_at)}` : ''}
        </span>
      </div>
      <h3 className={`mt-3 text-lg font-semibold leading-snug ${isRead ? 'text-slate-400 line-through' : 'text-white'}`}>
        <RichText text={item.title} glossary={glossary} />
      </h3>

      {points.length ? (
        <>
          <ul className="mt-3 list-disc space-y-1.5 pl-5 text-[15px] leading-6 text-slate-200">
            {points.map((point, index) => (
              <li key={index}>
                <RichText text={point} glossary={glossary} />
              </li>
            ))}
          </ul>
          <div className="mt-1 text-xs italic text-slate-500">{summaryOrigin(item.ai_source)}</div>
        </>
      ) : item.teaser ? (
        <p className="mt-3 text-sm leading-6 text-slate-300">
          <RichText text={item.teaser} glossary={glossary} />
        </p>
      ) : null}

      {reason ? <div className="mt-3 text-sm text-amber-400">👀 {reason} Open the source to read it.</div> : null}

      <div className="mt-4 flex flex-wrap items-center gap-4 text-sm">
        {item.flag === 'ACT' ? (
          <span className="font-medium text-red-300">Check the source before acting.</span>
        ) : null}
        <a
          href={item.link}
          target="_blank"
          rel="noreferrer"
          className="font-semibold text-sky-300 underline-offset-4 hover:underline"
        >
          {item.intake === 'email' ? 'Open in Gmail →' : 'Source →'}
        </a>
        <label className="ml-auto flex items-center gap-2 text-slate-400">
          <input type="checkbox" checked={isRead} onChange={onToggleRead} className="h-4 w-4 accent-sky-500" />
          Read
        </label>
      </div>
    </article>
  )
}

function BoardModal({
  board,
  glossary,
  readIds,
  onToggleRead,
  onClose,
  onDownload,
}: {
  board: Board
  glossary: GlossaryEntry[]
  readIds: Set<string>
  onToggleRead: (id: string) => void
  onClose: () => void
  onDownload: () => void
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 backdrop-blur-sm sm:items-center"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-label={board.title}
        className="my-8 max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl border border-slate-700 bg-slate-900 p-6 shadow-2xl sm:p-8"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-2 flex items-start justify-between gap-4">
          <h2 className="text-2xl font-bold text-white">
            {board.icon} {board.title}
          </h2>
          <div className="flex shrink-0 items-center gap-2">
            <DownloadButton label={board.title} onClick={onDownload} />
            <button onClick={onClose} aria-label="Close" className="rounded-full px-2 text-xl text-slate-400 hover:text-slate-200">
              ✕
            </button>
          </div>
        </div>
        {board.blurb ? <p className="text-sm text-slate-400">{board.blurb}</p> : null}
        <div className="mt-3 flex flex-wrap gap-2">
          {FLAG_ORDER.map((flag) => {
            const count = board.items.filter((item) => item.flag === flag).length
            return count ? <Pill key={flag} flag={flag} count={count} /> : null
          })}
        </div>
        <div className="mt-6 space-y-4">
          {board.items.map((item) => (
            <Story
              key={item.id}
              item={item}
              glossary={glossary}
              isRead={readIds.has(item.id)}
              onToggleRead={() => onToggleRead(item.id)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export function CategoryBoard({
  items,
  glossary,
  readIds,
  onToggleRead,
  generatedAt,
}: {
  items: DigestItem[]
  glossary: GlossaryEntry[]
  readIds: Set<string>
  onToggleRead: (id: string) => void
  generatedAt: string
}) {
  const { urgency, topics } = useMemo(() => buildBoards(items), [items])
  const [openKey, setOpenKey] = useState<string | null>(null)
  const open = [...urgency, ...topics].find((board) => board.key === openKey) || null
  const download = (title: string, list: DigestItem[]) =>
    saveText(sweepFilename(title, generatedAt), buildSweep(title, list, glossary, generatedAt))

  const tile = (board: Board) => {
    const unread = board.items.filter((item) => !readIds.has(item.id)).length
    const lead = board.items.find((item) => !readIds.has(item.id)) || board.items[0]
    const highlight =
      board.key === 'flag:ACT'
        ? 'border-red-500/50 bg-red-500/5 hover:border-red-400'
        : board.key === 'flag:KNOW'
          ? 'border-orange-500/40 bg-orange-500/5 hover:border-orange-400'
          : board.key === 'flag:NOTE'
            ? 'border-green-500/40 bg-green-500/5 hover:border-green-400'
            : board.key === 'unread'
              ? 'border-amber-500/40 bg-amber-500/5 hover:border-amber-400'
              : 'border-slate-800 bg-slate-900 hover:border-slate-600'
    const isTopic = board.key.startsWith('topic:')
    return (
      <div
        key={board.key}
        role="button"
        tabIndex={0}
        onClick={() => setOpenKey(board.key)}
        onKeyDown={(event) => (event.key === 'Enter' || event.key === ' ') && setOpenKey(board.key)}
        className={`flex cursor-pointer flex-col gap-3 rounded-2xl border p-5 text-left transition-colors ${highlight}`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="text-lg font-semibold text-white">
            <span className="mr-1.5">{board.icon}</span>
            {board.title}
          </div>
          <div className="shrink-0 text-right">
            <div className="text-2xl font-bold text-white">{board.items.length}</div>
            {unread < board.items.length ? <div className="text-[11px] text-slate-500">{unread} unread</div> : null}
          </div>
        </div>
        {/* Only topics carry the urgency bar: an urgency box is one colour. */}
        {isTopic ? <UrgencyBar items={board.items} /> : board.blurb ? (
          <div className="text-xs text-slate-400">{board.blurb}</div>
        ) : null}
        {lead ? <div className="line-clamp-2 text-sm leading-5 text-slate-400">{lead.title}</div> : null}
        <div className="mt-auto flex items-center justify-between">
          <span className="text-xs font-semibold text-sky-300">Open →</span>
          <DownloadButton label={board.title} onClick={() => download(board.title, board.items)} />
        </div>
      </div>
    )
  }

  return (
    <section className="mt-10">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-2xl font-semibold text-white">By urgency</h2>
        <button
          type="button"
          onClick={() => download('The whole week', items)}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:border-sky-500 hover:text-sky-200"
        >
          ⬇ Download the whole week
        </button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{urgency.map(tile)}</div>

      <h2 className="mb-4 mt-10 text-2xl font-semibold text-white">By topic</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{topics.map(tile)}</div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
        {FLAG_ORDER.map((flag) => (
          <Pill key={flag} flag={flag} />
        ))}
        <span className="self-center">Tap a dotted word to see what it means.</span>
      </div>

      {open ? (
        <BoardModal
          board={open}
          glossary={glossary}
          readIds={readIds}
          onToggleRead={onToggleRead}
          onClose={() => setOpenKey(null)}
          onDownload={() => download(open.title, open.items)}
        />
      ) : null}
    </section>
  )
}
