import { summaryOrigin, summaryPoints, type DigestItem } from './digest'
import { FLAG_LABELS } from './categories'
import { termName, termsIn, type GlossaryEntry } from './glossary'
import { slug } from './briefing'
import { formatDay } from './utils'

/**
 * A group of stories as one Markdown file, to send a friend or hand to an AI
 * tool for an overview: each headline, its dot points, who wrote them, and
 * the link. Our own summaries and the publisher's public headline and teaser
 * only; never the article text the summariser read.
 */
export function buildSweep(
  title: string,
  items: DigestItem[],
  glossary: GlossaryEntry[],
  generatedAt?: string | null
): string {
  const week = formatDay(generatedAt || new Date().toISOString())
  const lines = [
    `# Advice Monitor: ${title}`,
    '',
    `Week of ${week} · ${items.length} stor${items.length === 1 ? 'y' : 'ies'}`,
    '',
    '> Each story has a short summary and a link to the original. To get an overview, paste this into an AI',
    '> tool and ask: "What are the main themes, and what should an adviser do this week?" Read an Act now',
    '> story at its source before acting on it.',
    '',
  ]

  const used = new Map<string, GlossaryEntry>()
  items.forEach((item) => {
    const { emoji, label } = FLAG_LABELS[item.flag]
    const meta = [item.source_name, formatDay(item.created_at), item.topic].filter(Boolean).join(' · ')
    lines.push(`## ${emoji} ${label}: ${item.title || 'Untitled'}`, '', meta, '')
    const points = summaryPoints(item.ai_summary)
    if (points.length) {
      points.forEach((point) => lines.push(`- ${point}`))
      lines.push('', `_${summaryOrigin(item.ai_source)}_`)
    } else if (item.teaser) {
      lines.push(`Publisher's teaser: ${item.teaser}`)
    }
    lines.push('', `Link: ${item.link}`, '')
    termsIn(`${item.title} ${item.ai_summary || item.teaser || ''}`, glossary).forEach((entry) =>
      used.set(entry.term, entry)
    )
  })

  if (used.size) {
    lines.push('## Terms used', '')
    Array.from(used.values())
      .sort((a, b) => a.term.localeCompare(b.term))
      .forEach((entry) => lines.push(`- **${termName(entry)}**: ${entry.means}`))
    lines.push('')
  }
  return lines.join('\n')
}

export function sweepFilename(title: string, generatedAt?: string | null): string {
  return `advice-monitor-${slug(title)}-${(generatedAt || new Date().toISOString()).slice(0, 10)}.md`
}

/** Save text as a file in the browser. */
export function saveText(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = name
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
