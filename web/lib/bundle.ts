import type { BriefingEntry } from './briefing'
import type { DigestItem } from './digest'

/**
 * The two files that make a downloaded briefing usable on its own.
 *
 * Unzip the bundle before this existed and you got a handful of Markdown
 * files with no entry point: nothing said which digest they came from, what
 * to do with them, or where the boundary was. README.md answers the first
 * three questions and links.md is the list of sources to open by hand.
 *
 * Kept in step with src/monitor.py's format_bundle_readme and
 * format_bundle_links — two routes, one output, or they drift.
 */

/** Titles and teasers travel; article text never does. */
export const BOUNDARY =
  'Boundary: this bundle holds titles and teasers only. Do not ask a tool to fetch the links — ' +
  'open them yourself, in your own browser.'

function day(generatedAt?: string | null): string {
  return (generatedAt || new Date().toISOString()).slice(0, 10)
}

export function bundleReadme(entries: BriefingEntry[], generatedAt?: string | null): string {
  const items = entries.reduce((sum, entry) => sum + entry.items, 0)
  const pastes = entries.reduce((sum, entry) => sum + entry.pastes, 0)

  const lines = [
    `# Briefing bundle — ${day(generatedAt)}`,
    '',
    `From the Industry Update Monitor digest generated ${day(generatedAt)}.`,
    `${items} item${items === 1 ? '' : 's'} across ${entries.length} file${entries.length === 1 ? '' : 's'}, ` +
      `${pastes} paste${pastes === 1 ? '' : 's'} in total.`,
    '',
    '## What to do with it',
    '',
    '1. Open one `.md` file. Each is one subject, and each paste inside it is sized for one',
    '   chat message.',
    '2. Paste a block into the AI tool of your choice. The prompt is already at the top of it.',
    '3. Paste the reply back with `python src/monitor.py --import-summaries FILE`, or into the',
    '   dashboard. Replies are matched on the six-character ID at the start of each line, so',
    '   they land on the right items whichever file they came from.',
    '4. `links.md` is every item once, with its link, for opening sources yourself.',
    '',
    '## The rule',
    '',
    BOUNDARY,
    '',
    'A summary is triage. A 🔴 ACT item is read at its original source before it is acted on,',
    'no matter what any summary says.',
    '',
    '## Files',
    '',
  ]

  entries.forEach((entry) => {
    lines.push(
      `- \`${entry.name}\` — ${entry.label}: ${entry.items} item${entry.items === 1 ? '' : 's'}, ` +
        `${entry.pastes} paste${entry.pastes === 1 ? '' : 's'}`
    )
  })
  lines.push('')

  return lines.join('\n')
}

export function bundleLinks(items: DigestItem[], generatedAt?: string | null): string {
  const lines = [
    `# Links — ${day(generatedAt)}`,
    '',
    'Every item once, in digest order. Open these yourself; do not hand the list to a tool to',
    'fetch.',
    '',
  ]

  items.forEach((item) => {
    const id = item.ref || item.id || '——————'
    lines.push(`## ${id} · ${item.flag} · ${escapePipes(item.title || 'Untitled')}`)
    lines.push('')
    lines.push(`- Source: ${item.source_name || 'Unknown'}`)
    lines.push(`- Date: ${(item.created_at || '').slice(0, 10) || 'not recorded'}`)
    if (item.intake === 'email') {
      // A newsletter's link opens the message in its owner's own mailbox. It
      // is not a public article and must not be offered as one.
      lines.push(`- Newsletter — opens in your own mailbox, not a public page: ${item.link}`)
    } else {
      lines.push(`- Link: ${item.link}`)
    }
    lines.push('')
  })

  return lines.join('\n')
}

function escapePipes(text: string): string {
  return text.replace(/\|/g, '/')
}

/**
 * Every link, grouped by publisher — the dashboard's Bibliography as a file.
 * Markdown links, so it opens as a clickable list in any notes app or AI tool.
 */
export function bundleLinksBySource(items: DigestItem[], generatedAt?: string | null): string {
  const bySource = new Map<string, DigestItem[]>()
  items.forEach((item) => {
    const name = item.source_name || 'Unknown'
    if (!bySource.has(name)) bySource.set(name, [])
    bySource.get(name)!.push(item)
  })
  const lines = [`# Sources and links — ${day(generatedAt)}`, '']
  Array.from(bySource.keys())
    .sort((a, b) => a.localeCompare(b))
    .forEach((name) => {
      const articles = bySource.get(name)!
      lines.push(`## ${name} (${articles.length})`, '')
      articles.forEach((item) => {
        const title = (item.title || 'Untitled').replace(/[[\]]/g, '')
        lines.push(`- [${title}](${item.link}) — ${item.flag}, ${item.topic || 'General'}`)
      })
      lines.push('')
    })
  return lines.join('\n')
}
