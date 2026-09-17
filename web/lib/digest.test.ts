import { describe, expect, it } from 'vitest'
import { classifyLinkExactness, getItems, getStats, normalizeIncomingItem, summaryOrigin, type DigestItem } from './digest'

function item(overrides: Partial<DigestItem> = {}): DigestItem {
  return normalizeIncomingItem({
    title: 'ASIC bans a former director',
    teaser: 'The regulator has banned a former director for ten years.',
    link: 'https://www.example.com/asic-bans-a-former-director/',
    source_name: 'Test Source',
    flag: 'ACT',
    topic: 'Regulation',
    created_at: new Date().toISOString(),
    ...overrides,
  })
}

describe('classifyLinkExactness', () => {
  it('keeps an article whose path contains a section word', () => {
    // The old rule matched "/news/" anywhere and demoted every Financial
    // Standard and Riskinfo story to "fallback", where the filter hid them.
    for (const url of [
      'https://www.financialstandard.com.au/news/asic-zeroes-in-on-breaches-179813924',
      'https://riskinfo.com.au/news/2026/09/02/insurer-sanctioned-over-serious-breaches/',
    ]) {
      expect(classifyLinkExactness(url)).toBe('exact')
    }
  })

  it('calls a section landing page a fallback', () => {
    for (const url of [
      'https://www.asic.gov.au/newsroom',
      'https://www.afca.org.au/news/',
      'https://treasury.gov.au/consultation',
    ]) {
      expect(classifyLinkExactness(url)).toBe('fallback')
    }
  })

  it('calls a path with no article slug a fallback', () => {
    expect(classifyLinkExactness('https://www.example.com/about')).toBe('fallback')
  })

  it('calls a bare host, or anything unparseable, broad', () => {
    expect(classifyLinkExactness('https://www.abs.gov.au')).toBe('broad')
    expect(classifyLinkExactness('https://www.abs.gov.au/')).toBe('broad')
    expect(classifyLinkExactness('not a url')).toBe('broad')
    expect(classifyLinkExactness('')).toBe('broad')
  })
})

describe('getItems', () => {
  const items = [
    item({ flag: 'ACT', source_name: 'ifa', title: 'ASIC fines three super funds' }),
    item({ flag: 'KNOW', source_name: 'FAAA', title: 'Adviser numbers rise again' }),
    item({
      flag: 'NOTE',
      source_name: 'ifa',
      title: 'Fund managers share an outlook',
      created_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
    }),
  ]

  it('returns everything by default', () => {
    // Defaulting to "exact" silently dropped a fifth of the digest.
    expect(getItems(items)).toHaveLength(3)
  })

  it('filters by flag, source and free text', () => {
    expect(getItems(items, { flag: 'ACT' })).toHaveLength(1)
    expect(getItems(items, { source: 'ifa' })).toHaveLength(2)
    expect(getItems(items, { query: 'adviser numbers' })).toHaveLength(1)
  })

  it('matches a source name case-insensitively', () => {
    expect(getItems(items, { source: 'IFA' })).toHaveLength(2)
  })

  it('drops items outside the date range', () => {
    expect(getItems(items, { dateRange: 'month' })).toHaveLength(2)
    expect(getItems(items, { dateRange: 'all' })).toHaveLength(3)
  })

  it('caps the result at the limit', () => {
    expect(getItems(items, { limit: 2 })).toHaveLength(2)
  })
})

describe('getStats', () => {
  it('counts by flag and says nothing about read state', () => {
    const stats = getStats([item({ flag: 'ACT' }), item({ flag: 'KNOW' }), item({ flag: 'KNOW' })])
    expect(stats).toEqual({ total: 3, act: 1, know: 2, note: 0 })
  })
})

describe('summaryOrigin', () => {
  it('says a hand-written summary was written by hand', () => {
    expect(summaryOrigin('manual')).toBe('Summarised by hand')
  })

  it('names the local model rather than calling it a summary', () => {
    expect(summaryOrigin('ollama:qwen3:8b')).toBe('Summarised by a local model (qwen3:8b)')
  })

  it('admits an unrecorded origin', () => {
    expect(summaryOrigin(null)).toContain('origin not recorded')
  })
})
