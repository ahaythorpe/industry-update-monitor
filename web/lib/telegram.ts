import { summaryPoints, type DigestItem, type Flag } from './digest'
import { buildBoards } from './categories'
import { termName, termsIn, type GlossaryEntry } from './glossary'

/**
 * The Telegram message, in the same shape as src/telegram_sender.py's
 * format_telegram_digest. Two renderers, one output: if this drifts from the
 * Python one, the dashboard button and the Sunday run send different
 * messages, which is what happened here until 24 Sep 2026.
 *
 * Since 1 Oct 2026 a short weekly briefing, not the full newsletter (that is
 * the email): up to five stories under urgency headings, each its headline
 * and what happened; a word of the week from the glossary; the rest counted
 * by topic; and a link to the dashboard. One message, never split.
 *
 * Telegram's HTML parse mode is used, so every piece of publisher text is
 * escaped: a headline containing "<b>" must not be able to break the message.
 */

// Telegram caps a message at 4096 characters.
export const MAX_BODY = 3900
export const PUBLIC_DASHBOARD = 'https://advice-monitor.vercel.app'
export const TOP_STORIES = 5

const FLAG_SEQUENCE: Flag[] = ['ACT', 'KNOW', 'NOTE']
const FLAG_HEADINGS: Record<Flag, string> = {
  ACT: '🔴 <b>Act now</b>',
  KNOW: '🟠 <b>Worth knowing</b>',
  NOTE: '🟢 <b>Background</b>',
}
const FLAG_WORDS: Record<Flag, string> = { ACT: 'act now', KNOW: 'worth knowing', NOTE: 'background' }

/** Same as Python's html.escape(text, quote=True). */
export function escapeHtml(text: string): string {
  return (text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
}

const bold = (escaped: string) => escaped.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')

/** Act now first; a summarised story before one the model could not read; then confidence. */
function rank(items: DigestItem[]): DigestItem[] {
  const order = (item: DigestItem) => {
    const n = FLAG_SEQUENCE.indexOf(item.flag)
    return n === -1 ? 3 : n
  }
  return [...items].sort(
    (a, b) =>
      order(a) - order(b) ||
      Number(!a.ai_summary) - Number(!b.ai_summary) ||
      (b.confidence || 0) - (a.confidence || 0)
  )
}

function story(item: DigestItem): string {
  const title = escapeHtml(item.title || 'Untitled')
  const head = item.link ? `<a href="${escapeHtml(item.link)}">${title}</a>` : title
  const [first] = summaryPoints(item.ai_summary)
  return `• ${head}\n   ${first ? bold(escapeHtml(first)) : '<i>Not summarised: open the source.</i>'}`
}

/** ISO week number, which turns the word of the week the same way as Python's isocalendar(). */
export function isoWeek(date: Date): number {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7))
  const start = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
  return Math.ceil(((d.getTime() - start.getTime()) / 86400000 + 1) / 7)
}

function wordOfTheWeek(items: DigestItem[], glossary: GlossaryEntry[], week: number): string[] {
  const found = new Map<string, GlossaryEntry>()
  items.forEach((item) =>
    termsIn(`${item.title || ''} ${item.ai_summary || item.teaser || ''}`, glossary).forEach((entry) => {
      if (!found.has(entry.term)) found.set(entry.term, entry)
    })
  )
  const terms = Array.from(found.values())
  if (!terms.length) return []
  const entry = terms[week % terms.length]
  return ['', `📖 <b>${escapeHtml(termName(entry))}</b>: ${escapeHtml(entry.means || '')}`]
}

export function formatTelegramDigest(
  items: DigestItem[],
  options: {
    focus?: Flag | null
    dashboard?: string | null
    today?: string
    glossary?: GlossaryEntry[]
    week?: number
  } = {}
): string {
  const { focus = null, glossary = [] } = options
  const dashboard = options.dashboard || PUBLIC_DASHBOARD
  const week = options.week ?? isoWeek(new Date())
  const chosen = focus ? items.filter((item) => item.flag === focus) : items
  const today =
    options.today || new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'short' }).format(new Date())
  const lines = [`📰 <b>Advice Monitor${focus ? ': extra' : ''}</b> · week to ${escapeHtml(today)}`]
  if (focus) lines.push(`<i>Only: ${focus}</i>`)
  if (!chosen.length) return [...lines, '', 'Nothing matched this week.'].join('\n')
  const counts = FLAG_SEQUENCE.filter((flag) => chosen.some((item) => item.flag === flag))
    .map((flag) => `${chosen.filter((item) => item.flag === flag).length} ${FLAG_WORDS[flag]}`)
    .join(' · ')
  lines.push(`${chosen.length} stor${chosen.length === 1 ? 'y' : 'ies'}: ${counts}`)
  if (!focus && !chosen.some((item) => item.flag === 'ACT')) lines.push('Nothing this week changes what you must do.')

  const footer = '\n<i>Check an Act now story at its source before acting.</i>'
  const tail = (picked: DigestItem[]) => {
    const rest = chosen.filter((item) => !picked.includes(item))
    const out = wordOfTheWeek(picked, glossary, week)
    if (rest.length) {
      const byTopic = buildBoards(rest)
        .topics.map((board) => `${board.icon} ${escapeHtml(board.title)} ${board.items.length}`)
        .join(' · ')
      const acts = rest.filter((item) => item.flag === 'ACT').length
      out.push('', `<b>${rest.length} more${acts ? ` (${acts} act now)` : ''}:</b> ${byTopic}`)
    }
    out.push(`👉 <a href="${escapeHtml(dashboard)}">Read them on the dashboard</a>`)
    return out
  }
  const body = (picked: DigestItem[]) =>
    FLAG_SEQUENCE.flatMap((flag) => {
      const flagged = picked.filter((item) => item.flag === flag)
      return flagged.length ? ['', FLAG_HEADINGS[flag], ...flagged.map(story)] : []
    })

  const picked: DigestItem[] = []
  for (const item of rank(chosen).slice(0, TOP_STORIES)) {
    if ([...lines, ...body([...picked, item]), ...tail([...picked, item])].join('\n').length + footer.length > MAX_BODY) break
    picked.push(item)
  }
  return [...lines, ...body(picked), ...tail(picked)].join('\n') + footer
}

/**
 * Telegram's error description, in words that say what to do about it.
 * Telegram's own text is kept on the end so nothing is hidden.
 */
export function explainTelegramError(description?: string | null, status?: number): string {
  const raw = (description || '').trim()
  const text = raw.toLowerCase()
  let plain: string
  if (status === 401 || text.includes('unauthorized')) {
    plain = 'Telegram did not recognise the bot token. Copy it again from BotFather into TELEGRAM_BOT_TOKEN.'
  } else if (text.includes('chat not found')) {
    plain =
      'Telegram could not find your chat. Open the bot in Telegram, press Start, then have the chat ID looked up again.'
  } else if (text.includes('blocked by the user')) {
    plain = 'You have blocked the bot in Telegram. Unblock it, press Start, and try again.'
  } else if (text.includes("can't initiate conversation") || text.includes('bot can\'t send messages')) {
    plain = 'The bot is not allowed to message you yet. Open it in Telegram and press Start.'
  } else if (status === 429 || text.includes('too many requests')) {
    plain = 'Telegram asked to slow down. Wait a minute and try again.'
  } else if (text.includes("can't parse entities") || text.includes('message is too long')) {
    plain = 'Telegram could not read the message formatting. That is a bug in this tool, not your settings — ask Claude to look.'
  } else {
    plain = 'Telegram refused the message.'
  }
  return raw ? `${plain} (Telegram said: “${raw}”)` : plain
}
