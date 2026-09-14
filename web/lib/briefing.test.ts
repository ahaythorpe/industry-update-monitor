import { describe, expect, it } from 'vitest'
import { BRIEF_PROMPT, briefingFilename, buildBriefing, groupItems, slug } from './briefing'
import type { DigestItem } from './digest'

const TOPICS = ['Compliance', 'Regulation', 'Super & tax', 'Insurance', 'People moves', 'Business', 'Industry']

function item(overrides: Partial<DigestItem> & { ref?: string | null }): DigestItem {
  return {
    id: overrides.link || 'id',
    ref: 'aaaaaa',
    title: 'ASIC bans a director',
    teaser: 'The regulator banned a director for ten years.',
    link: 'https://a.test/story',
    source_name: 'Test Source',
    flag: 'ACT',
    topic: 'Compliance',
    is_read: false,
    created_at: '2026-09-13T00:00:00Z',
    ...overrides,
  } as DigestItem
}

const MIXED = [
  item({ ref: 'a00001', link: 'https://a.test/1', topic: 'Compliance', flag: 'ACT' }),
  item({ ref: 'a00002', link: 'https://a.test/2', topic: 'Compliance', flag: 'KNOW' }),
  item({ ref: 'a00003', link: 'https://a.test/3', topic: 'Regulation', flag: 'ACT' }),
  item({ ref: 'a00004', link: 'https://a.test/4', topic: 'People moves', flag: 'NOTE' }),
]

describe('grouping', () => {
  it('follows the category order the digest published', () => {
    expect(groupItems(MIXED, ['topic'], TOPICS).map((group) => group.label)).toEqual([
      'Compliance',
      'Regulation',
      'People moves',
    ])
  })

  it('runs ACT first when grouping by flag', () => {
    expect(groupItems(MIXED, ['flag'], TOPICS).map((group) => group.label)).toEqual([
      'ACT',
      'KNOW',
      'NOTE',
    ])
  })

  it('nests flags inside categories when asked for both', () => {
    expect(groupItems(MIXED, ['topic', 'flag'], TOPICS).map((group) => group.name)).toEqual([
      'compliance-act',
      'compliance-know',
      'regulation-act',
      'people-moves-note',
    ])
  })

  it('groups the other way round when the order is reversed', () => {
    expect(groupItems(MIXED, ['flag', 'topic'], TOPICS)[0].label).toBe('ACT · Compliance')
  })

  it('leaves out a combination that holds nothing', () => {
    const labels = groupItems(MIXED, ['topic', 'flag'], TOPICS).map((group) => group.label)
    expect(labels).not.toContain('Compliance · NOTE')
    expect(labels).not.toContain('Insurance · ACT')
  })

  it('still groups a category the published order does not name', () => {
    const odd = [item({ ref: 'a00005', topic: 'Something new' })]
    expect(groupItems(odd, ['topic'], TOPICS)[0].label).toBe('Something new')
  })

  it('treats no grouping as one group of everything', () => {
    expect(groupItems(MIXED, [], TOPICS)).toHaveLength(1)
  })

  it('makes a safe filename from a label', () => {
    expect(slug('Super & tax')).toBe('super-tax')
    expect(slug('People moves')).toBe('people-moves')
  })
})

describe('the downloaded briefing', () => {
  it('carries the safeguards prompt in every paste', () => {
    const { text, pastes } = buildBriefing(MIXED, ['topic'], TOPICS)
    expect(pastes).toBe(3)
    expect(text.match(/summarise ONLY from the teaser given/g)).toHaveLength(3)
    expect(text).toContain(BRIEF_PROMPT.split('\n')[0])
  })

  it('names the group in the paste marker', () => {
    const { text } = buildBriefing(MIXED, ['topic', 'flag'], TOPICS)
    expect(text).toContain('<!-- Compliance · KNOW — paste 1 of 1 -->')
  })

  it('marks pastes plainly when nothing is grouped', () => {
    const { text } = buildBriefing(MIXED, [], TOPICS)
    expect(text).toContain('<!-- paste 1 of 1 -->')
  })

  it('carries only the title, teaser and link of each item', () => {
    const { text } = buildBriefing([MIXED[0]], [], TOPICS)
    expect(text).toContain('ID: a00001')
    expect(text).toContain('TITLE: ASIC bans a director')
    expect(text).toContain('TEASER: The regulator banned a director for ten years.')
    expect(text).toContain('LINK: https://a.test/1')
    // Nothing else of the item reaches the file: no body, no source metadata.
    expect(text.split('\n').filter((line) => line.startsWith('ID: '))).toHaveLength(1)
  })

  it('says so rather than showing nothing when a teaser is empty', () => {
    const { text } = buildBriefing([item({ ref: 'a00009', teaser: '' })], [], TOPICS)
    expect(text).toContain('TEASER: (none)')
  })

  it('splits a group too big for one paste without splitting an item', () => {
    const many = Array.from({ length: 7 }, (_, n) =>
      item({ ref: `b0000${n}`, link: `https://a.test/b${n}`, topic: 'Compliance', flag: 'ACT' })
    )
    const { text, pastes } = buildBriefing(many, ['topic'], TOPICS, 3)
    expect(pastes).toBe(3)
    expect(text).toContain('<!-- Compliance — paste 3 of 3 -->')
    expect(text.match(/^ID: /gm)).toHaveLength(7)
  })

  it('leaves out an item with no ID rather than inventing one', () => {
    const result = buildBriefing([MIXED[0], item({ ref: null })], [], TOPICS)
    expect(result.items).toBe(1)
    expect(result.skipped).toBe(1)
    expect(result.text.match(/^ID: /gm)).toHaveLength(1)
  })

  it('produces nothing at all when there is nothing to brief', () => {
    expect(buildBriefing([], ['topic'], TOPICS)).toMatchObject({ text: '', items: 0, pastes: 0 })
  })

  it('names the file after the grouping and the digest date', () => {
    expect(briefingFilename(['topic', 'flag'], '2026-09-13T21:36:09Z')).toBe(
      'briefing-topic-flag-2026-09-13.md'
    )
    expect(briefingFilename([], '2026-09-13T21:36:09Z')).toBe('briefing-2026-09-13.md')
  })
})
