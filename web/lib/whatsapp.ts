import { summaryOrigin, type DigestItem, type Flag } from './digest'

/**
 * The WhatsApp newsletter, in the same shape as src/whatsapp_sender.py.
 *
 * The dashboard used to build its own title-only list with no length cap: a
 * 50-item digest produced one body of several thousand characters, which
 * WhatsApp rejects at 1600. Splitting happens on item boundaries so an article
 * is never cut in half, and a section continued into the next part repeats its
 * heading.
 */

// Leave room for the " (1/3)" part counter appended to each body.
export const MAX_BODY = 1500

const FLAG_HEADINGS: Record<Flag, string> = {
  ACT: '🔴 *ACT — action required*',
  KNOW: '🟠 *KNOW — worth knowing*',
  NOTE: '🟢 *NOTE — background*',
}

const FLAG_SEQUENCE: Flag[] = ['ACT', 'KNOW', 'NOTE']

// Neutralise WhatsApp markup characters inside publisher text, so a headline
// containing an asterisk cannot unbalance the message's own bold markers.
function escapeMarkup(text: string): string {
  return (text || '').replace(/\*/g, '･').replace(/_/g, ' ').replace(/~/g, '-').replace(/`/g, "'")
}

function itemBlock(index: number, item: DigestItem): string {
  const lines = [`*${index}. ${escapeMarkup(item.title || 'Untitled')}*`]

  const meta: string[] = []
  if (item.source_name) meta.push(escapeMarkup(item.source_name))
  // Confidence is shown only where it means "trust this flag". On a NOTE it
  // means "confidently background", which reads as importance if shown.
  if (typeof item.confidence === 'number' && (item.flag === 'ACT' || item.flag === 'KNOW')) {
    meta.push(`${Math.round(item.confidence * 100)}% confidence`)
  }
  if (meta.length) lines.push(`_${meta.join(' · ')}_`)

  // The summary you had written reached the dashboard and stopped there
  // (IMPROVEMENTS.md item 4). src/whatsapp_sender.py was fixed then; this
  // renderer was missed, so the dashboard button silently sent the publisher's
  // teaser instead. Labelled with who wrote it, in italics, so it never reads
  // as the publisher's own words, and placed above the teaser rather than
  // instead of it.
  const written = escapeMarkup(item.ai_summary || '').trim()
  if (written) {
    lines.push(`_${escapeMarkup(summaryOrigin(item.ai_source))}:_ ${written}`)
  }

  const teaser = escapeMarkup(item.teaser).trim()
  if (teaser) lines.push(teaser)
  if (item.link) lines.push(item.link)

  return lines.join('\n')
}

export function formatWhatsappDigest(
  items: DigestItem[],
  perFlagLimit = 6,
  weekOf?: string
): string[] {
  const byFlag: Record<Flag, DigestItem[]> = { ACT: [], KNOW: [], NOTE: [] }
  items.forEach((item) => {
    if (byFlag[item.flag]) byFlag[item.flag].push(item)
  })

  const total = FLAG_SEQUENCE.reduce((sum, flag) => sum + byFlag[flag].length, 0)
  const week =
    weekOf ||
    new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date())

  type Block = { text: string; heading: string | null; isHeading?: boolean }
  const blocks: Block[] = [
    { text: `📰 *Industry Update Monitor*\n_Week of ${week} · ${total} items_`, heading: null },
  ]

  FLAG_SEQUENCE.forEach((flag) => {
    const group = byFlag[flag].slice(0, perFlagLimit)
    if (!group.length) return
    let heading = FLAG_HEADINGS[flag]
    if (byFlag[flag].length > group.length) {
      heading += ` _(top ${group.length} of ${byFlag[flag].length})_`
    }
    blocks.push({ text: heading, heading, isHeading: true })
    group.forEach((item, position) => {
      blocks.push({ text: itemBlock(position + 1, item), heading })
    })
  })

  if (total === 0) {
    blocks.push({ text: '_Nothing cleared the filters this week._', heading: null })
  }

  const messages: string[] = []
  let current = ''
  blocks.forEach((block) => {
    const candidate = current ? `${current}\n\n${block.text}` : block.text
    if (candidate.length > MAX_BODY && current) {
      messages.push(current)
      current =
        block.heading && !block.isHeading
          ? `${block.heading} _(cont.)_\n\n${block.text}`
          : block.text
    } else {
      current = candidate
    }
  })
  if (current) messages.push(current)

  if (messages.length === 1) return messages
  return messages.map((body, index) => `${body}\n\n_(${index + 1}/${messages.length})_`)
}
