import { describe, expect, it } from 'vitest'
import { splitTerms, termName, termsIn, type GlossaryEntry } from './glossary'

const glossary: GlossaryEntry[] = [
  { term: 'CSLR', also: ['Compensation Scheme of Last Resort'], means: 'pays clients of collapsed firms.' },
  { term: 'ART', also: ['Administrative Review Tribunal'], means: 'reviews government decisions.' },
  { term: 'best interests duty', also: ['BID'], means: 'act in the client’s best interests.' },
]

describe('glossary', () => {
  it('matches an acronym only in capitals, as a whole word', () => {
    expect(termsIn('The CSLR levy rises', glossary).map((t) => t.term)).toEqual(['CSLR'])
    expect(termsIn('the art of advice', glossary)).toEqual([])
    expect(termsIn('PARTNERS', glossary)).toEqual([])
  })

  it('matches an ordinary phrase in any case', () => {
    expect(termsIn('The Best Interests Duty applies', glossary).map((t) => t.term)).toEqual(['best interests duty'])
  })

  it('names an acronym with its full name in brackets', () => {
    expect(termName(glossary[0])).toBe('CSLR (Compensation Scheme of Last Resort)')
    expect(termName(glossary[2])).toBe('best interests duty')
  })

  it('splits text around terms and keeps every character', () => {
    const text = 'Treasury said the CSLR, and the ART, will act.'
    const runs = splitTerms(text, glossary)
    expect(runs.map((r) => r.text).join('')).toBe(text)
    expect(runs.filter((r) => r.entry).map((r) => r.text)).toEqual(['CSLR', 'ART'])
  })

  it('prefers the longer spelling where two overlap', () => {
    const runs = splitTerms('the Compensation Scheme of Last Resort pays', glossary)
    expect(runs.filter((r) => r.entry).map((r) => r.text)).toEqual(['Compensation Scheme of Last Resort'])
  })
})
