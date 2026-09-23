import { describe, expect, it } from 'vitest'
import { normalizeIncomingItem, type DigestItem, type Flag } from './digest'
import {
  DEFAULT_PER_FLAG,
  MAX_BODY,
  MAX_PER_FLAG,
  clampPerFlag,
  explainTelegramError,
  formatTelegramDigest,
} from './telegram'

function item(n: number, flag: Flag = 'ACT', overrides: Partial<DigestItem> = {}): DigestItem {
  return normalizeIncomingItem({
    title: `Story ${n} <b>`,
    teaser: 'Teaser '.repeat(50),
    link: `https://a.test/${n}`,
    source_name: 'ifa',
    flag,
    topic: 'Industry',
    ...overrides,
  })
}

const many = (count: number, flag: Flag = 'ACT') => Array.from({ length: count }, (_, n) => item(n, flag))

// Mirrors tests/test_telegram.py, so the dashboard button and --telegram
// cannot quietly send different newsletters.
describe('formatTelegramDigest', () => {
  it('splits a long digest under the cap and numbers the parts', () => {
    const messages = formatTelegramDigest(many(60), null)
    expect(messages.length).toBeGreaterThan(1)
    messages.forEach((message) => expect(message.length).toBeLessThanOrEqual(4096))
    messages.forEach((message) => expect(message.length).toBeLessThanOrEqual(MAX_BODY + 40))
    expect(messages[messages.length - 1]).toMatch(new RegExp(`\\(${messages.length} of ${messages.length}\\)</i>$`))
  })

  it('never cuts an article in half', () => {
    const messages = formatTelegramDigest(many(60), null)
    messages.forEach((message) => {
      expect(message.split('<a ').length).toBe(message.split('</a>').length)
    })
  })

  it('sends a short digest as one message with no part counter', () => {
    const messages = formatTelegramDigest(many(2))
    expect(messages).toHaveLength(1)
    expect(messages[0]).not.toContain(' of 1)')
  })

  it('labels a summary with who wrote it and escapes titles', () => {
    const [message] = formatTelegramDigest([
      item(1, 'ACT', { ai_summary: 'ASIC banned an adviser.', ai_source: 'ollama:qwen3:8b' }),
    ])
    expect(message).toContain('ASIC banned an adviser.')
    expect(message).toContain('Summarised by a local model (qwen3:8b)')
    expect(message).toContain('Story 1 &lt;b&gt;')
    expect(message).not.toContain('Story 1 <b>')
    expect(message).toContain('href="https://a.test/1"')
  })

  it('labels a hand-written summary as hand-written', () => {
    const [message] = formatTelegramDigest([item(1, 'ACT', { ai_summary: 'Mine.', ai_source: 'manual' })])
    expect(message).toContain('Summarised by hand')
  })

  it('falls back to the publisher teaser, capped, when there is no summary', () => {
    const [message] = formatTelegramDigest([item(1)])
    expect(message).not.toContain('Summarised')
    expect(message).toContain('Teaser')
    expect(message).toContain('…')
  })

  it('cannot have a link break out of its attribute', () => {
    const [message] = formatTelegramDigest([item(1, 'ACT', { link: 'https://a.test/"><script>' })])
    expect(message).not.toContain('"><script>')
  })

  it('orders the sections ACT, then KNOW, then NOTE, and counts them', () => {
    const [message] = formatTelegramDigest([item(1, 'NOTE'), item(2, 'ACT'), item(3, 'KNOW')], 6, '23 September 2026')
    expect(message).toContain('Advice Monitor — 23 September 2026')
    expect(message).toContain('1 ACT · 1 KNOW · 1 NOTE')
    expect(message.indexOf('ACT — act')).toBeLessThan(message.indexOf('KNOW — worth'))
    expect(message.indexOf('KNOW — worth')).toBeLessThan(message.indexOf('NOTE — background'))
  })

  it('applies the per-flag limit', () => {
    const body = formatTelegramDigest(many(20, 'KNOW'), 3).join('\n')
    expect(body).toContain('3. <a')
    expect(body).not.toContain('4. <a')
  })
})

describe('clampPerFlag', () => {
  it('keeps a request body from asking for an unbounded digest', () => {
    expect(clampPerFlag(undefined)).toBe(DEFAULT_PER_FLAG)
    expect(clampPerFlag('10')).toBe(DEFAULT_PER_FLAG)
    expect(clampPerFlag(Number.NaN)).toBe(DEFAULT_PER_FLAG)
    expect(clampPerFlag(0)).toBe(1)
    expect(clampPerFlag(-5)).toBe(1)
    expect(clampPerFlag(1e9)).toBe(MAX_PER_FLAG)
    expect(clampPerFlag(4.7)).toBe(4)
  })
})

describe('explainTelegramError', () => {
  it('turns Telegram errors into what to do next', () => {
    expect(explainTelegramError('Unauthorized', 401)).toContain('bot token')
    expect(explainTelegramError('Bad Request: chat not found', 400)).toContain('press Start')
    expect(explainTelegramError('Forbidden: bot was blocked by the user', 403)).toContain('Unblock')
    expect(explainTelegramError('Too Many Requests: retry after 5', 429)).toContain('Wait')
  })

  it('keeps Telegram’s own words on the end', () => {
    expect(explainTelegramError('Bad Request: chat not found')).toContain('Telegram said: “Bad Request: chat not found”')
    expect(explainTelegramError(undefined)).toBe('Telegram refused the message.')
  })
})
