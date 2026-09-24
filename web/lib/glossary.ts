/**
 * The hand-written glossary (data/glossary.json), matched the same way as
 * src/monitor.py's terms_in: whole words only, and case-sensitive when the
 * spelling is an acronym, so "ART" is the tribunal and "the art of advice" is
 * not. Nothing is inferred; a term is found because its own spelling is there.
 */

export type GlossaryEntry = {
  term: string
  also?: string[]
  means: string
  matters?: string
}

export type TermRun = { text: string; entry?: GlossaryEntry }

function spellingsOf(entry: GlossaryEntry): string[] {
  return [entry.term, ...(entry.also || [])]
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function isAcronym(spelling: string): boolean {
  return spelling === spelling.toUpperCase() && /[A-Z]/.test(spelling)
}

function patternFor(spelling: string, global = false): RegExp {
  const flags = (isAcronym(spelling) ? '' : 'i') + (global ? 'g' : '')
  return new RegExp(`(?<![\\w])${escapeRegExp(spelling)}(?![\\w])`, flags)
}

/** "CSLR (Compensation Scheme of Last Resort)" for an acronym, else the term. */
export function termName(entry: GlossaryEntry): string {
  const full = entry.also?.[0]
  return isAcronym(entry.term) && full ? `${entry.term} (${full})` : entry.term
}

/** Which terms appear in a piece of text, in the glossary's order. */
export function termsIn(text: string, glossary: GlossaryEntry[], limit = 4): GlossaryEntry[] {
  const found: GlossaryEntry[] = []
  for (const entry of glossary) {
    if (spellingsOf(entry).some((spelling) => patternFor(spelling).test(text || ''))) {
      found.push(entry)
      if (limit && found.length >= limit) break
    }
  }
  return found
}

/**
 * Split text into plain runs and runs that are a glossary term, so each term
 * can be shown underlined with its meaning. The longest spelling wins where
 * two overlap ("Compensation Scheme of Last Resort" over "CSLR").
 */
export function splitTerms(text: string, glossary: GlossaryEntry[]): TermRun[] {
  const hits: { start: number; end: number; entry: GlossaryEntry }[] = []
  for (const entry of glossary) {
    for (const spelling of spellingsOf(entry)) {
      for (const match of (text || '').matchAll(patternFor(spelling, true))) {
        hits.push({ start: match.index!, end: match.index! + match[0].length, entry })
      }
    }
  }
  hits.sort((a, b) => a.start - b.start || b.end - a.end)

  const runs: TermRun[] = []
  let cursor = 0
  for (const hit of hits) {
    if (hit.start < cursor) continue
    if (hit.start > cursor) runs.push({ text: text.slice(cursor, hit.start) })
    runs.push({ text: text.slice(hit.start, hit.end), entry: hit.entry })
    cursor = hit.end
  }
  if (cursor < (text || '').length) runs.push({ text: text.slice(cursor) })
  return runs
}
