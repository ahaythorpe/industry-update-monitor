import { describe, expect, it } from 'vitest'
import { normalizeIncomingItem, type DigestItem, type Flag } from './digest'
import { MAX_BODY, formatWhatsappDigest } from './whatsapp'

function items(count: number, flag: Flag = 'KNOW'): DigestItem[] {
  return Array.from({ length: count }, (_, index) =>
    normalizeIncomingItem({
      title: `Item number ${index}`,
      teaser: 'A short summary sentence from the publisher.',
      link: `https://a.test/story-number-${index}`,
      source_name: 'Test Source',
      flag,
      topic: 'Industry',
      confidence: 0.9,
    })
  )
}

function withSummary(overrides: Partial<DigestItem> = {}): DigestItem {
  return normalizeIncomingItem({
    title: 'CSLR levy changes',
    teaser: 'The publisher brief sentence.',
    link: 'https://a.test/cslr',
    source_name: 'Test Source',
    flag: 'ACT',
    topic: 'Industry',
    confidence: 0.9,
    ...overrides,
  })
}

// IMPROVEMENTS.md item 4 fixed src/whatsapp_sender.py and missed this
// renderer, so the dashboard button sent the publisher's teaser and dropped
// the summary without saying so. Two routes, one output, or they drift.
describe('summaries reach the WhatsApp message', () => {
  it('includes a hand-written summary, labelled, above the teaser', () => {
    const body = formatWhatsappDigest([
      withSummary({ ai_summary: 'What this means for advisers.', ai_source: 'manual' }),
    ]).join('\n')

    expect(body).toContain('What this means for advisers.')
    expect(body).toContain('Summarised by hand')
    // Above, never instead of: the publisher's words stay on the message.
    expect(body).toContain('The publisher brief sentence.')
    expect(body.indexOf('What this means for advisers.')).toBeLessThan(
      body.indexOf('The publisher brief sentence.')
    )
  })

  it('names the local model rather than presenting it as this tool', () => {
    const body = formatWhatsappDigest([
      withSummary({ ai_summary: 'A local summary.', ai_source: 'ollama:qwen3:8b' }),
    ]).join('\n')

    expect(body).toContain('Summarised by a local model (qwen3:8b)')
  })

  it('says nothing at all when there is no summary', () => {
    const body = formatWhatsappDigest([withSummary()]).join('\n')

    expect(body).not.toContain('Summarised')
    expect(body).toContain('The publisher brief sentence.')
  })
})

describe('formatWhatsappDigest', () => {
  it('sends a short digest as a single message', () => {
    const messages = formatWhatsappDigest(items(2))
    expect(messages).toHaveLength(1)
    expect(messages[0]).toContain('Industry Update Monitor')
  })

  it('keeps every part under the WhatsApp body cap', () => {
    // The dashboard route used to build one unbounded body; WhatsApp rejects
    // anything over 1600 characters.
    const messages = formatWhatsappDigest(items(40), 40)
    expect(messages.length).toBeGreaterThan(1)
    messages.forEach((body) => expect(body.length).toBeLessThanOrEqual(MAX_BODY + 40))
  })

  it('reintroduces the heading when a section spills into the next part', () => {
    const messages = formatWhatsappDigest(items(40), 40)
    messages.slice(1).forEach((body) => expect(body).toContain('_(cont.)_'))
  })

  it('orders the sections ACT, then KNOW, then NOTE', () => {
    const combined = formatWhatsappDigest([
      ...items(1, 'NOTE'),
      ...items(1, 'ACT'),
      ...items(1, 'KNOW'),
    ]).join('\n')
    expect(combined.indexOf('ACT — action')).toBeLessThan(combined.indexOf('KNOW — worth'))
    expect(combined.indexOf('KNOW — worth')).toBeLessThan(combined.indexOf('NOTE — background'))
  })

  it('hides confidence on a NOTE, where it would read as importance', () => {
    expect(formatWhatsappDigest(items(1, 'NOTE'))[0]).not.toContain('confidence')
    expect(formatWhatsappDigest(items(1, 'ACT'))[0]).toContain('confidence')
  })

  it('cannot have its formatting broken by markup in publisher text', () => {
    const [body] = formatWhatsappDigest([
      normalizeIncomingItem({
        title: 'A *bold* claim_here',
        teaser: 'Text with *stars*',
        link: 'https://a.test/a-bold-claim',
        source_name: 'Test Source',
        flag: 'ACT',
        topic: 'Industry',
        confidence: 0.9,
      }),
    ])
    expect(body).not.toContain('*bold*')
    expect(body.split('*').length % 2).toBe(1) // balanced bold markers
  })

  it('says so when nothing cleared the filters', () => {
    expect(formatWhatsappDigest([])[0]).toContain('Nothing cleared the filters')
  })

  it('reports the per-flag cap it applied', () => {
    expect(formatWhatsappDigest(items(20), 3).join('\n')).toContain('top 3 of 20')
  })
})
