import { summaryPoints, type DigestItem, type Flag } from './digest'
import { buildBoards } from './categories'

/**
 * The Telegram message, in the same shape as src/telegram_sender.py's
 * format_telegram_digest. Two renderers, one output: if this drifts from the
 * Python one, the dashboard button and the Monday run send different
 * messages, which is what happened here until 24 Sep 2026.
 *
 * One message, never split: headlines by urgency, Act now first, each with
 * its first dot point; what does not fit is counted. With the dashboard online
 * (DASHBOARD_URL) it is the short alert: Act now only, the week by topic in
 * one line, and a link. The button cannot attach the newsletter file the
 * Monday run sends, so without a dashboard it lists every urgency instead.
 *
 * Telegram's HTML parse mode is used, so every piece of publisher text is
 * escaped: a headline containing "<b>" must not be able to break the message.
 */

// Telegram caps a message at 4096 characters.
export const MAX_BODY = 3900

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

function line(item: DigestItem): string {
  const title = escapeHtml(item.title || 'Untitled')
  const head = item.link ? `<a href="${escapeHtml(item.link)}">${title}</a>` : title
  const [first] = summaryPoints(item.ai_summary)
  return `▪️ ${head}` + (first ? `\n    ${escapeHtml(first).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')}` : '')
}

export function formatTelegramDigest(
  items: DigestItem[],
  options: { focus?: Flag | null; dashboard?: string | null; today?: string } = {}
): string {
  const { focus = null, dashboard = null } = options
  const chosen = focus ? items.filter((item) => item.flag === focus) : items
  const today =
    options.today ||
    new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date())
  const lines = [`📰 <b>Advice Monitor: ${focus ? 'extra update' : 'weekly update'}</b>`, escapeHtml(today)]
  if (focus) lines.push(`<i>Only: ${focus}</i>`)
  lines.push('')
  if (!chosen.length) {
    lines.push('Nothing matched this week.')
    return lines.join('\n')
  }
  const counts = FLAG_SEQUENCE.filter((flag) => chosen.some((item) => item.flag === flag))
    .map((flag) => `${chosen.filter((item) => item.flag === flag).length} ${FLAG_WORDS[flag]}`)
    .join(' · ')
  lines.push(`${chosen.length} stor${chosen.length === 1 ? 'y' : 'ies'}: ${counts}`)

  const listed: Flag[] = focus || !dashboard ? FLAG_SEQUENCE : ['ACT']
  if (dashboard && !focus && !chosen.some((item) => item.flag === 'ACT')) {
    lines.push('', 'Nothing this week changes what you must do.')
  }

  const tail: string[] = []
  if (dashboard) {
    const byTopic = buildBoards(chosen)
      .topics.map((board) => `${board.icon} ${escapeHtml(board.title)} ${board.items.length}`)
      .join(' · ')
    tail.push('', `<b>By topic:</b> ${byTopic}`, '', `👉 <a href="${escapeHtml(dashboard)}">Open this week on the dashboard</a>`)
  }
  const footer = '\n<i>Summaries are a quick guide. Read an Act now story at its source before acting on it.</i>'

  let leftOut = 0
  listed.forEach((flag) => {
    const flagged = chosen.filter((item) => item.flag === flag)
    if (!flagged.length) return
    const section = ['', FLAG_HEADINGS[flag]]
    flagged.forEach((item) => {
      const candidate = [...lines, ...section, line(item), ...tail].join('\n') + footer
      if (candidate.length > MAX_BODY - 120) leftOut += 1
      else section.push(line(item))
    })
    if (section.length > 2) lines.push(...section)
  })
  if (leftOut) lines.push('', `<b>+ ${leftOut} more on the dashboard</b>`)
  return [...lines, ...tail].join('\n') + footer
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
