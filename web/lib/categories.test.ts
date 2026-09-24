import { describe, expect, it } from 'vitest'
import { buildBoards, unreadReason } from './categories'
import type { DigestItem } from './digest'

function item(id: string, flag: DigestItem['flag'], topic: string, extra: Partial<DigestItem> = {}): DigestItem {
  return {
    id, title: `Story ${id}`, teaser: '', link: `https://a.test/${id}`, source_name: 'ifa',
    flag, topic, is_read: false, created_at: '2026-09-22', ai_summary: '• **A fact** here.',
    body_source: 'feed_content', ...extra,
  }
}

describe('buildBoards', () => {
  const items = [
    item('1', 'KNOW', 'Super & tax'),
    item('2', 'ACT', 'Regulation'),
    item('3', 'KNOW', 'Super & tax'),
    item('4', 'NOTE', 'General', { body_source: 'feed_summary' }),
  ]
  const { urgency, topics } = buildBoards(items)

  it('keeps urgency apart from topic', () => {
    expect(urgency.map((b) => b.title)).toEqual(['Act now', 'Worth knowing', 'Background', 'Read these yourself'])
    expect(urgency[0].items.map((i) => i.id)).toEqual(['2'])
    expect(topics.some((b) => b.title === 'Act now')).toBe(false)
  })

  it('orders topics by urgent stories, then size', () => {
    expect(topics.map((b) => b.title)).toEqual(['Regulation', 'Super & tax', 'General'])
  })

  it('gives each topic an icon', () => {
    expect(topics.find((b) => b.title === 'Super & tax')?.icon).toBe('💰')
  })
})

describe('unreadReason', () => {
  it('flags a teaser-only story, a thin summary and a missing one', () => {
    expect(unreadReason(item('a', 'KNOW', 'General', { body_source: 'feed_summary' }))).toMatch(/teaser/)
    expect(unreadReason(item('b', 'KNOW', 'General', { ai_summary: '• Thin story. Open the source.' }))).toMatch(/little/)
    expect(unreadReason(item('c', 'KNOW', 'General', { ai_summary: null }))).toMatch(/Not summarised/)
    expect(unreadReason(item('d', 'KNOW', 'General'))).toBeNull()
  })
})
