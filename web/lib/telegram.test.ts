import { describe, expect, it } from 'vitest'
import { normalizeIncomingItem, type DigestItem, type Flag } from './digest'
import { MAX_BODY, PUBLIC_DASHBOARD, TOP_STORIES, explainTelegramError, formatTelegramDigest, isoWeek } from './telegram'

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
const twoPoints = { ai_summary: '• What happened here. • **A key fact.** • A third point.' }
const glossary = [{ term: 'ASIC', also: ['Australian Securities and Investments Commission'], means: 'the regulator.', matters: 'it acts.' }]

describe('formatTelegramDigest', () => {
  it('names the top stories, Act now first, and counts the rest', () => {
    const message = formatTelegramDigest([...many(80, 'KNOW'), item(99, 'ACT')])
    expect(message.length).toBeLessThanOrEqual(MAX_BODY)
    expect(message.indexOf('Story 99')).toBeLessThan(message.indexOf('Story 0 '))
    expect(message.split('<a href="https://a.test/').length - 1).toBe(TOP_STORIES)
    expect(message).toContain(`<b>${81 - TOP_STORIES} more:</b>`)
    expect(message).toContain('🔴 <b>Act now</b>')
    expect(message).toContain(`href="${PUBLIC_DASHBOARD}"`)
  })

  it('escapes titles and cannot have a link break out of its attribute', () => {
    const message = formatTelegramDigest([item(1, 'ACT', { link: 'https://a.test/"><script>' })])
    expect(message).toContain('Story 1 &lt;b&gt;')
    expect(message).not.toContain('"><script>')
  })

  it('gives each story its headline and what happened, bold kept', () => {
    const message = formatTelegramDigest([item(1, 'ACT', { ai_summary: '• **ASIC** banned him. • Second point.' })])
    expect(message).toContain('\n   <b>ASIC</b> banned him.')
    expect(message).not.toContain('Second point')
  })

  it('ranks a story the model could not read below one it did, and says so', () => {
    const message = formatTelegramDigest([item(1, 'ACT'), item(2, 'ACT', twoPoints)])
    expect(message).toContain('Not summarised: open the source.')
    expect(message.indexOf('Story 2 ')).toBeLessThan(message.indexOf('Story 1 '))
  })

  it('counts Act now stories left out', () => {
    expect(formatTelegramDigest(many(TOP_STORIES + 3))).toContain('<b>3 more (3 act now):</b>')
  })

  it('explains a word of the week from the glossary', () => {
    const message = formatTelegramDigest([item(1, 'ACT', { ai_summary: '• ASIC issued a stop order.' })], { glossary })
    expect(message).toContain('📖 <b>ASIC (Australian Securities and Investments Commission)</b>: the regulator.')
  })

  it('uses plain words', () => {
    const message = formatTelegramDigest([item(1, 'NOTE'), item(2, 'ACT'), item(3, 'KNOW')], { today: '24 Sept' })
    expect(message).toContain('week to 24 Sept')
    expect(message).toContain('1 act now · 1 worth knowing · 1 background')
  })

  it('says when nothing needs action, and takes another dashboard address', () => {
    const message = formatTelegramDigest([item(1, 'KNOW')], { dashboard: 'https://monitor.example/' })
    expect(message).toContain('Nothing this week changes what you must do.')
    expect(message).toContain('href="https://monitor.example/"')
  })

  it('an extra send lists only the urgency asked for', () => {
    const message = formatTelegramDigest([item(1, 'ACT'), item(2, 'KNOW')], { focus: 'KNOW' })
    expect(message).toContain('Advice Monitor: extra</b>')
    expect(message).toContain('Only: KNOW')
    expect(message).not.toContain('Story 1 ')
  })

  it('counts weeks the way Python does', () => {
    expect(isoWeek(new Date(2026, 9, 1))).toBe(40)
    expect(isoWeek(new Date(2027, 0, 1))).toBe(53)
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
