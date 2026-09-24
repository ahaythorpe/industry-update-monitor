'use client'

/**
 * Sources the monitor cannot read, as a drop-down of links to open by hand.
 *
 * The tool never fetches these pages. You open one, copy what you can
 * legitimately read, and paste it into Claude with the prompt below.
 */

import { useState } from 'react'
import {
  PASTE_PROMPT,
  REASON_LABEL,
  UNREACHABLE_SOURCES,
  type UnreachableReason,
} from '@/lib/unreachable'

const GROUPS: { reason: UnreachableReason; title: string }[] = [
  { reason: 'paywall', title: 'Paywalled: only paste what your own subscription lets you read' },
  { reason: 'blocks-bots', title: 'Free, but they block automated readers' },
  { reason: 'no-feed', title: 'Free, but no feed to subscribe to' },
]

export function UnreachableSources() {
  const [copied, setCopied] = useState<'idle' | 'copied' | 'failed'>('idle')

  async function copyPrompt() {
    try {
      await navigator.clipboard.writeText(PASTE_PROMPT)
      setCopied('copied')
    } catch {
      setCopied('failed')
    }
    setTimeout(() => setCopied('idle'), 2000)
  }

  return (
    <details className="mb-8 rounded-2xl border border-amber-900/60 bg-amber-950/20 p-5">
      <summary className="cursor-pointer text-sm font-semibold text-slate-300">
        Sources the monitor can&apos;t read ({UNREACHABLE_SOURCES.length}), open these yourself
      </summary>

      <div className="mt-4 flex flex-col gap-4">
        <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4 text-xs text-slate-300">
          <p>
            The monitor never opens these pages. To get one summarised: open it, copy the article
            text, then paste it into Claude under this prompt.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              onClick={copyPrompt}
              className={`rounded-xl border px-4 py-2 text-sm font-semibold transition-colors ${
                copied === 'failed'
                  ? 'border-amber-600/60 bg-amber-600/15 text-amber-200'
                  : 'border-sky-600/60 bg-sky-600/15 text-sky-200 hover:bg-sky-600/25'
              }`}
            >
              {copied === 'copied' ? '✓ Copied' : copied === 'failed' ? 'Copy failed' : 'Copy prompt for Claude'}
            </button>
            <span className="text-slate-500">
              A 🔴 Act now item is still read at its source.
            </span>
          </div>
        </div>

        {GROUPS.map((group) => {
          const sources = UNREACHABLE_SOURCES.filter((source) => source.reason === group.reason)
          return (
            <section key={group.reason}>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                {group.title}
              </h3>
              <ul className="space-y-2">
                {sources.map((source) => (
                  <li
                    key={source.name}
                    className="flex flex-col gap-1 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 sm:flex-row sm:items-baseline sm:justify-between sm:gap-4"
                  >
                    <div>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-semibold text-sky-300 hover:underline"
                      >
                        {source.name} ↗
                      </a>
                      <p className="text-xs text-slate-400">{source.why}</p>
                    </div>
                    <span className="shrink-0 text-[11px] text-slate-500">
                      {REASON_LABEL[source.reason]}
                      {source.checked ? `, checked ${source.checked}` : ', not checked yet'}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )
        })}
      </div>
    </details>
  )
}
