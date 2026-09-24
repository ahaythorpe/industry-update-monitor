import { summaryPoints, type DigestItem, type Flag } from './digest'

/**
 * What a reader sees instead of ACT / KNOW / NOTE, and an icon per category.
 * Kept in step with _LABELS and _ICONS in src/email_sender.py, so the
 * dashboard and the newsletter use the same words.
 */
export const FLAG_LABELS: Record<Flag, { emoji: string; label: string }> = {
  ACT: { emoji: '🔴', label: 'Act now' },
  KNOW: { emoji: '🟠', label: 'Worth knowing' },
  NOTE: { emoji: '🟢', label: 'Background' },
}

export const FLAG_ORDER: Flag[] = ['ACT', 'KNOW', 'NOTE']

const ICONS: Record<string, string> = {
  Regulation: '⚖️',
  Compliance: '✅',
  'Super & tax': '💰',
  Insurance: '🛡️',
  'Key personnel movements': '👥',
  Business: '🏢',
  'Markets & investing': '📈',
  'Fees & pricing': '🏷️',
  'Practice & technology': '💻',
  General: '📰',
}

export function categoryIcon(topic: string): string {
  return ICONS[topic] || '📌'
}

/** Why the model could not summarise a story, or null. Mirrors unread_reason. */
export function unreadReason(item: DigestItem): string | null {
  const summary = (item.ai_summary || '').toLowerCase()
  if (item.body_source === 'feed_summary') return 'The publisher only shares a teaser.'
  if (summary.includes('thin') && summary.includes('open')) return 'Too little text to summarise.'
  if (!summaryPoints(item.ai_summary).length) return 'Not summarised yet.'
  return null
}

export type Board = { key: string; icon: string; title: string; blurb?: string; items: DigestItem[] }

const URGENCY_BLURBS: Record<Flag, string> = {
  ACT: 'These change what you must do.',
  KNOW: 'Useful context on policy, people and the market.',
  NOTE: 'Data and reference material.',
}

/**
 * The boxes on the front page, in two rows kept apart: urgency (Act now,
 * Worth knowing, Background, then the stories to read by hand) and topic
 * (most urgent first, then biggest).
 */
export function buildBoards(items: DigestItem[]): { urgency: Board[]; topics: Board[] } {
  const rank = (item: DigestItem) => FLAG_ORDER.indexOf(item.flag)
  const byUrgency = (list: DigestItem[]) => [...list].sort((a, b) => rank(a) - rank(b))

  const urgency: Board[] = []
  FLAG_ORDER.forEach((flag) => {
    const flagged = items.filter((item) => item.flag === flag)
    if (flagged.length) {
      const { emoji, label } = FLAG_LABELS[flag]
      urgency.push({ key: `flag:${flag}`, icon: emoji, title: label, blurb: URGENCY_BLURBS[flag], items: flagged })
    }
  })
  const unread = items.filter((item) => unreadReason(item))
  if (unread.length) {
    urgency.push({
      key: 'unread',
      icon: '👀',
      title: 'Read these yourself',
      blurb: 'The summariser could not read these.',
      items: byUrgency(unread),
    })
  }

  const groups = new Map<string, DigestItem[]>()
  items.forEach((item) => {
    const topic = item.topic || 'General'
    if (!groups.has(topic)) groups.set(topic, [])
    groups.get(topic)!.push(item)
  })
  const acts = (list: DigestItem[]) => list.filter((item) => item.flag === 'ACT').length
  const topics = Array.from(groups.entries())
    .sort(
      ([a, x], [b, y]) =>
        acts(y) - acts(x) || y.length - x.length || Number(a === 'General') - Number(b === 'General') || a.localeCompare(b)
    )
    .map(([topic, list]) => ({ key: `topic:${topic}`, icon: categoryIcon(topic), title: topic, items: byUrgency(list) }))

  return { urgency, topics }
}
