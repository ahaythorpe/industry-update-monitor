import { summaryOrigin, summaryPoints, type DigestItem, type Flag } from './digest'

/**
 * The Telegram newsletter, in the same shape as src/telegram_sender.py.
 *
 * Telegram replaced WhatsApp on 23 Sep 2026: the Telegram Bot API is free with
 * no trial to run out and no per-message charge, where every WhatsApp route
 * (Twilio, Meta) eventually costs money. Two renderers, one output — if this
 * drifts from the Python one, the dashboard button and `--telegram` send
 * different newsletters, which is exactly what happened with WhatsApp
 * (IMPROVEMENTS.md item 4).
 *
 * Messages use Telegram's HTML parse mode, so every piece of publisher text is
 * escaped: a headline containing "<b>" must not be able to break the message.
 * Splitting happens only between articles, never inside one.
 */

// Telegram caps a message at 4096 characters; leave room for the part counter.
export const MAX_BODY = 3900

// Python's --per-flag default. The route clamps anything it is sent to this range.
export const DEFAULT_PER_FLAG = 6
export const MAX_PER_FLAG = 50

const FLAG_HEADINGS: Record<Flag, string> = {
  ACT: '🔴 <b>ACT — act on these</b>',
  KNOW: '🟠 <b>KNOW — worth knowing</b>',
  NOTE: '🟢 <b>NOTE — background</b>',
}

const FLAG_SEQUENCE: Flag[] = ['ACT', 'KNOW', 'NOTE']

/** Same as Python's html.escape(text, quote=True). */
export function escapeHtml(text: string): string {
  return (text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
}

function itemBlock(index: number, item: DigestItem): string {
  const title = escapeHtml(item.title || 'Untitled')
  const lines = [
    item.link
      ? `<b>${index}. <a href="${escapeHtml(item.link)}">${title}</a></b>`
      : `<b>${index}. ${title}</b>`,
  ]
  if (item.source_name) lines.push(`<i>${escapeHtml(item.source_name)}</i>`)

  // A summary is always labelled with who wrote it, so it never reads as the
  // publisher's words or as this tool's own work. Without one, the publisher's
  // public teaser, capped — never the full article.
  const written = (item.ai_summary || '').trim()
  if (written) {
    summaryPoints(written).forEach((point) =>
      lines.push('• ' + escapeHtml(point).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>'))
    )
    lines.push(`<i>— ${escapeHtml(summaryOrigin(item.ai_source))}</i>`)
  } else if (item.teaser) {
    const teaser = item.teaser
    lines.push(escapeHtml(teaser.slice(0, 280) + (teaser.length > 280 ? '…' : '')))
  }
  return lines.join('\n')
}

export function formatTelegramDigest(
  items: DigestItem[],
  perFlagLimit: number | null = DEFAULT_PER_FLAG,
  today?: string
): string[] {
  const date =
    today ||
    new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date())
  const count = (flag: Flag) => items.filter((item) => item.flag === flag).length
  const header =
    `📰 <b>Advice Monitor — ${escapeHtml(date)}</b>\n` +
    `${count('ACT')} ACT · ${count('KNOW')} KNOW · ${count('NOTE')} NOTE`

  const blocks = [header]
  FLAG_SEQUENCE.forEach((flag) => {
    let flagged = items.filter((item) => item.flag === flag)
    if (perFlagLimit) flagged = flagged.slice(0, perFlagLimit)
    if (!flagged.length) return
    blocks.push(FLAG_HEADINGS[flag])
    flagged.forEach((item, position) => blocks.push(itemBlock(position + 1, item)))
  })
  blocks.push('<i>Summaries are triage. Read an ACT item at its source before acting on it.</i>')

  const messages: string[] = []
  let current = ''
  blocks.forEach((block) => {
    const candidate = current ? `${current}\n\n${block}` : block
    if (candidate.length > MAX_BODY && current) {
      messages.push(current)
      current = block
    } else {
      current = candidate
    }
  })
  if (current) messages.push(current)

  if (messages.length === 1) return messages
  return messages.map((message, index) => `${message}\n\n<i>(${index + 1} of ${messages.length})</i>`)
}

/** A per-flag limit from an untrusted request body, forced into 1..MAX_PER_FLAG. */
export function clampPerFlag(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return DEFAULT_PER_FLAG
  return Math.min(MAX_PER_FLAG, Math.max(1, Math.floor(value)))
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
