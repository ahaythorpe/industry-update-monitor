import type { DigestItem, Flag } from './digest'

/**
 * The paste-ready briefing, in the same shape as src/monitor.py.
 *
 * The dashboard could already filter to "the KNOW items in Compliance" but
 * had no way to get them out, so the only route to an AI tool was the CLI's
 * `--brief`, which knew nothing about what was on screen. This builds the
 * identical file from whatever the filters currently show.
 *
 * Identical matters: the prompt is SAFEGUARDS.md section D verbatim and the
 * IDs are the refs the monitor wrote, so a reply to a briefing downloaded
 * here imports through `--import-summaries` exactly like one from the CLI.
 *
 * What goes in a briefing is the feed's own title and teaser and nothing
 * else — the same two fields the monitor read from the RSS feed. No article
 * body is fetched here or anywhere else, so there is nothing behind a
 * paywall for this file to carry.
 */

// src/monitor.py BRIEF_PROMPT, character for character.
export const BRIEF_PROMPT = `You are helping a trainee financial adviser triage this week's Australian
advice-industry news. You will be given items, each with an ID, a TITLE, a public TEASER, and a
LINK. For each item output one line: \`ID | FLAG | one-sentence summary | LINK\`. FLAG is ACT
(changes what an adviser must do), KNOW (useful context), or NOTE (background/data). Rules:
summarise ONLY from the teaser given; never invent detail or add facts not present; if the teaser
is too thin, write "thin — open source"; always keep the ID and the LINK unchanged; do not attempt
to access anything beyond the text provided.`

// src/monitor.py BRIEF_CHUNK: a comfortable paste for one chat message.
export const BRIEF_CHUNK = 15

export type Dimension = 'topic' | 'flag'
export type Grouping = Dimension[]

const FLAG_SEQUENCE: Flag[] = ['ACT', 'KNOW', 'NOTE']

export type Group = { label: string; name: string; items: DigestItem[] }

/** `Super & tax` -> `super-tax`, so a label can name a file. */
export function slug(label: string): string {
  return label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

/**
 * Split items by the combination of dimensions asked for.
 *
 * `topicOrder` comes from the digest itself rather than a copy of the
 * classifier's labels kept here, which would drift the first time a rule was
 * added. A combination with nothing in it is left out, so the download never
 * contains an empty heading.
 */
export function groupItems(
  items: DigestItem[],
  grouping: Grouping,
  topicOrder: string[]
): Group[] {
  if (!grouping.length) return [{ label: 'All items', name: 'briefing', items: [...items] }]

  const keyOf: Record<Dimension, (item: DigestItem) => string> = {
    topic: (item) => item.topic || 'Industry',
    flag: (item) => item.flag,
  }
  const orderOf: Record<Dimension, string[]> = {
    // A category present in the items but missing from the published order
    // still gets a group, after the ones the classifier named.
    topic: [...topicOrder, ...items.map((item) => item.topic || 'Industry')].filter(
      (label, index, all) => all.indexOf(label) === index
    ),
    flag: FLAG_SEQUENCE,
  }

  const buckets = new Map<string, DigestItem[]>()
  items.forEach((item) => {
    const key = grouping.map((dimension) => keyOf[dimension](item)).join('\u0000')
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key)!.push(item)
  })

  // Every combination in order, keeping only those that hold something.
  let combinations: string[][] = [[]]
  grouping.forEach((dimension) => {
    combinations = combinations.flatMap((prefix) =>
      orderOf[dimension].map((label) => [...prefix, label])
    )
  })

  return combinations
    .map((combination) => ({
      label: combination.join(' · '),
      name: combination.map(slug).join('-'),
      items: buckets.get(combination.join('\u0000')) || [],
    }))
    .filter((group) => group.items.length > 0)
}

/** One item as the four lines the prompt describes. */
function itemBlock(item: DigestItem): string {
  return [
    `ID: ${item.ref}`,
    `TITLE: ${item.title}`,
    `TEASER: ${item.teaser || '(none)'}`,
    `LINK: ${item.link}`,
  ].join('\n')
}

/** Render items as paste-ready blocks, never splitting one across two. */
export function formatBriefing(items: DigestItem[], chunkSize = BRIEF_CHUNK): string[] {
  const blocks: string[] = []
  for (let start = 0; start < items.length; start += chunkSize) {
    const batch = items.slice(start, start + chunkSize)
    blocks.push([BRIEF_PROMPT, '', ...batch.map((item) => `${itemBlock(item)}\n`)].join('\n').trim())
  }
  return blocks
}

export type BriefingFile = { text: string; items: number; pastes: number; skipped: number }

/**
 * Join per-group files into one briefing.
 *
 * Takes the files rather than the items, so downloading a chosen few groups —
 * just Super & tax · KNOW, say — produces exactly the text those groups would
 * have had as separate files, with nothing renumbered or re-chunked.
 */
export function combineBriefing(files: BriefingEntry[], skipped = 0): BriefingFile {
  // Each file ends with a newline of its own; the separator supplies its own.
  const parts = files.map((file) => file.text.replace(/\n$/, ''))
  return {
    text: parts.join('\n\n---\n\n') + (parts.length ? '\n' : ''),
    items: files.reduce((total, file) => total + file.items, 0),
    pastes: files.reduce((total, file) => total + file.pastes, 0),
    skipped,
  }
}

/**
 * Build the whole downloadable briefing.
 *
 * Assembled from the per-group files so the zip and the single file cannot
 * drift apart: one builder, two wrappers.
 *
 * An item with no ref is left out and counted, never given an invented ID: a
 * reply line whose ID matches nothing is reported by `--import-summaries`,
 * and a made-up one would instead attach a summary to the wrong article.
 */
export function buildBriefing(
  items: DigestItem[],
  grouping: Grouping,
  topicOrder: string[],
  chunkSize = BRIEF_CHUNK
): BriefingFile {
  const usable = items.filter((item) => Boolean(item.ref)).length
  return combineBriefing(
    buildBriefingFiles(items, grouping, topicOrder, chunkSize),
    items.length - usable
  )
}

export type BriefingEntry = { name: string; label: string; text: string; items: number; pastes: number }

/**
 * The same briefing as one file per group, for downloading as a folder.
 *
 * Each file is exactly what `--group-by` writes to
 * output/briefing/<name>.md, so the two routes stay interchangeable.
 */
export function buildBriefingFiles(
  items: DigestItem[],
  grouping: Grouping,
  topicOrder: string[],
  chunkSize = BRIEF_CHUNK
): BriefingEntry[] {
  const usable = items.filter((item) => Boolean(item.ref))

  return groupItems(usable, grouping, topicOrder).map((group) => {
    const blocks = formatBriefing(group.items, chunkSize)
    const text = blocks
      .map((block, index) => {
        const counter = `paste ${index + 1} of ${blocks.length}`
        const marker = grouping.length ? `${group.label} — ${counter}` : counter
        return `<!-- ${marker} -->\n\n${block}`
      })
      .join('\n\n---\n\n')

    return {
      name: `${group.name}.md`,
      label: group.label,
      text: text + '\n',
      items: group.items.length,
      pastes: blocks.length,
    }
  })
}

/** `briefing-topic-flag-2026-09-14.md` — says what it holds and when. */
export function briefingFilename(
  grouping: Grouping,
  generatedAt: string,
  extension: 'md' | 'zip' = 'md'
): string {
  const day = (generatedAt || new Date().toISOString()).slice(0, 10)
  return ['briefing', ...grouping, day].join('-') + '.' + extension
}
