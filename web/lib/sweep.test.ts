import { describe, expect, it } from 'vitest'
import { buildSweep, sweepFilename } from './sweep'
import type { DigestItem } from './digest'

const glossary = [{ term: 'CSLR', also: ['Compensation Scheme of Last Resort'], means: 'pays clients of collapsed firms.' }]

function item(extra: Partial<DigestItem> = {}): DigestItem {
  return {
    id: '1', title: 'Treasury opens CSLR levy consultation', teaser: 'A teaser.', link: 'https://a.test/1',
    source_name: 'ifa', flag: 'ACT', topic: 'Regulation', is_read: false, created_at: '2026-09-22',
    ai_summary: '• **Treasury** is consulting. • It closes in October.', ai_source: 'ollama:qwen3:8b',
    brief_text: 'THE WHOLE ARTICLE TEXT', ...extra,
  }
}

describe('buildSweep', () => {
  const text = buildSweep('Regulation', [item()], glossary, '2026-09-23T00:00:00Z')

  it('carries each headline, its dot points, who wrote them and the link', () => {
    expect(text).toContain('# Advice Monitor: Regulation')
    expect(text).toContain('## 🔴 Act now: Treasury opens CSLR levy consultation')
    expect(text).toContain('- **Treasury** is consulting.')
    expect(text).toContain('Summarised by a local model (qwen3:8b)')
    expect(text).toContain('Link: https://a.test/1')
  })

  it('explains the terms it uses', () => {
    expect(text).toContain('- **CSLR (Compensation Scheme of Last Resort)**: pays clients of collapsed firms.')
  })

  it('never carries the article text the summariser read', () => {
    expect(text).not.toContain('THE WHOLE ARTICLE TEXT')
  })

  it('falls back to the publisher teaser, labelled, when there is no summary', () => {
    expect(buildSweep('X', [item({ ai_summary: null })], [])).toContain("Publisher's teaser: A teaser.")
  })

  it('names the file after the group and the week', () => {
    expect(sweepFilename('Super & tax', '2026-09-23T00:00:00Z')).toBe('advice-monitor-super-tax-2026-09-23.md')
  })
})
