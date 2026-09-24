import { describe, expect, it } from 'vitest'
import { normalizeIncomingItem, type DigestItem, type Flag } from './digest'
import { MAX_BODY, explainTelegramError, formatTelegramDigest } from './telegram'

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
// cannot quietly send different messages.
describe('formatTelegramDigest', () => {
  it('is one message under the cap, Act now first, counting what did not fit', () => {
    const message = formatTelegramDigest([...many(80, 'KNOW'), item(99, 'ACT')])
    expect(message.length).toBeLessThanOrEqual(MAX_BODY)
    expect(message.indexOf('Story 99')).toBeLessThan(message.indexOf('Story 0 '))
    expect(message).toMatch(/\+ \d+ more on the dashboard/)
    expect(message).toContain('weekly update')
  })

  it('escapes titles and cannot have a link break out of its attribute', () => {
    const message = formatTelegramDigest([item(1, 'ACT', { link: 'https://a.test/"><script>' })])
    expect(message).toContain('Story 1 &lt;b&gt;')
    expect(message).not.toContain('"><script>')
  })

  it('shows the first dot point with its key fact bold', () => {
    const message = formatTelegramDigest([item(1, 'ACT', { ai_summary: '• **ASIC** banned him. • Second point.' })])
    expect(message).toContain('<b>ASIC</b> banned him.')
    expect(message).not.toContain('Second point')
  })

  it('uses plain words, in urgency order', () => {
    const message = formatTelegramDigest([item(1, 'NOTE'), item(2, 'ACT'), item(3, 'KNOW')], { today: '24 September 2026' })
    expect(message).toContain('24 September 2026')
    expect(message).toContain('1 act now · 1 worth knowing · 1 background')
    expect(message.indexOf('Act now</b>')).toBeLessThan(message.indexOf('Worth knowing</b>'))
    expect(message.indexOf('Worth knowing</b>')).toBeLessThan(message.indexOf('Background</b>'))
  })

  it('is a short Act now alert once the dashboard is online', () => {
    const message = formatTelegramDigest(
      [item(1, 'ACT', { topic: 'Regulation' }), item(2, 'KNOW', { topic: 'Super & tax' })],
      { dashboard: 'https://monitor.example/' }
    )
    expect(message).toContain('Story 1 ')
    expect(message).not.toContain('Story 2 ')
    expect(message).toContain('⚖️ Regulation 1 · 💰 Super &amp; tax 1')
    expect(message).toContain('href="https://monitor.example/"')
  })

  it('an extra send lists only the urgency asked for', () => {
    const message = formatTelegramDigest([item(1, 'ACT'), item(2, 'KNOW')], { focus: 'KNOW' })
    expect(message).toContain('extra update')
    expect(message).toContain('Only: KNOW')
    expect(message).not.toContain('Story 1 ')
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
