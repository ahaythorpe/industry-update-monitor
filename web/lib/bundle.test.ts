import { describe, expect, it } from 'vitest'
import { BOUNDARY, bundleLinks, bundleReadme } from './bundle'
import { normalizeIncomingItem, type DigestItem } from './digest'
import type { BriefingEntry } from './briefing'

function item(overrides: Partial<DigestItem> = {}): DigestItem {
  return normalizeIncomingItem({
    title: 'ASIC bans a director',
    teaser: 'The regulator banned a director for ten years.',
    link: 'https://a.test/asic-bans',
    source_name: 'Test Source',
    flag: 'ACT',
    topic: 'Industry',
    created_at: '2026-09-14T00:00:00+00:00',
    ...overrides,
  })
}

const entries: BriefingEntry[] = [
  { name: 'act.md', label: 'ACT', text: '', items: 9, pastes: 2 },
  { name: 'know.md', label: 'KNOW', text: '', items: 3, pastes: 1 },
]

// IMPROVEMENTS.md item 12 — unzipping used to give Markdown files with no
// entry point. Kept in step with src/monitor.py's format_bundle_* pair.
describe('bundleReadme', () => {
  it('says which digest it came from and how much of it there is', () => {
    const readme = bundleReadme(entries, '2026-09-14T00:00:00+00:00')

    expect(readme).toContain('# Briefing bundle — 2026-09-14')
    expect(readme).toContain('12 items across 2 files, 3 pastes')
    expect(readme).toContain('act.md')
  })

  it('carries the boundary and the round trip, not just the file list', () => {
    const readme = bundleReadme(entries, '2026-09-14T00:00:00+00:00')

    expect(readme).toContain(BOUNDARY)
    expect(readme).toContain('--import-summaries')
    expect(readme).toContain('read at its original source')
  })
})

describe('bundleLinks', () => {
  it('lists every item once with its link', () => {
    const links = bundleLinks([item(), item({ link: 'https://a.test/second' })])

    expect(links).toContain('- Link: https://a.test/asic-bans')
    expect(links).toContain('- Link: https://a.test/second')
  })

  it('labels a newsletter rather than offering it as a public article', () => {
    const links = bundleLinks([
      item({ intake: 'email', link: 'https://mail.google.com/mail/u/0/#inbox/abc' }),
    ])

    expect(links).toContain('opens in your own mailbox')
    expect(links).not.toContain('- Link: https://mail.google.com')
  })
})

describe('links by source', () => {
  it('groups every article under its publisher, each linked', async () => {
    const { bundleLinksBySource } = await import('./bundle')
    const text = bundleLinksBySource(
      [
        { title: 'One', link: 'https://a.test/1', source_name: 'SMSF Adviser', flag: 'KNOW', topic: 'Super & tax' },
        { title: 'Two', link: 'https://a.test/2', source_name: 'SMSF Adviser', flag: 'ACT', topic: 'Compliance' },
      ] as never,
      '2026-09-23'
    )
    expect(text).toContain('## SMSF Adviser (2)')
    expect(text).toContain('- [One](https://a.test/1) — KNOW, Super & tax')
    expect(text).toContain('- [Two](https://a.test/2)')
  })
})
