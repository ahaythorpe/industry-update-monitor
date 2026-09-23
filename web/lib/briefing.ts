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

// src/monitor.py DEEP_PROMPT: the second pass, for a narrowed set of items.
export const DEEP_PROMPT = `You are helping a trainee financial adviser understand this week's Australian
advice-industry news in depth. You will be given items, each with an ID, a TITLE, a SOURCE, a
DATE, the publisher's own text, and a LINK. For each item output one line:
\`ID | FLAG | summary | LINK\`. FLAG is ACT (changes what an adviser must do), KNOW (useful
context), or NOTE (background/data). Write two to four sentences, on a single line, and lead with
the specific facts — figures, dates, names, what changed — rather than the framing. Rules: use
ONLY the text provided; never invent detail or add facts not present; if the text runs to less
than about eighty words, write "thin — open source" and nothing else; say so if the DATE means a
figure or a poll may have been overtaken; always keep the ID and the LINK unchanged; do not
attempt to access anything beyond the text provided.`

// src/monitor.py BRIEF_CHUNK: a comfortable paste for one chat message.
export const BRIEF_CHUNK = 15

// src/monitor.py DEEP_CHUNK: deep items carry the publisher's own article
// text, so far fewer fit in one paste.
export const DEEP_CHUNK = 6

// src/monitor.py FALLBACK_TOPIC: where an item goes when no rule scores.
// Only used for an item that somehow arrived without a category — the digest
// publishes the real label list, so this is a floor, not a second opinion.
export const FALLBACK_TOPIC = 'General'

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
    topic: (item) => item.topic || FALLBACK_TOPIC,
    flag: (item) => item.flag,
  }
  const orderOf: Record<Dimension, string[]> = {
    // A category present in the items but missing from the published order
    // still gets a group, after the ones the classifier named.
    topic: [...topicOrder, ...items.map((item) => item.topic || FALLBACK_TOPIC)].filter(
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

/** One item, in the shape src/monitor.py writes. */
function itemBlock(item: DigestItem): string {
  return [
    `ID: ${item.ref}`,
    `TITLE: ${item.title}`,
    // Who published it and when: a masthead's view is not a regulator's, and
    // a poll or a quarterly figure can already have been overtaken.
    `SOURCE: ${item.source_name || '(unknown)'}`,
    `DATE: ${(item.created_at || '').slice(0, 10) || '(unknown)'}`,
    // brief_text is the fuller teaser; teaser is the short display version.
    `TEASER: ${item.brief_text || item.teaser || '(none)'}`,
    `LINK: ${item.link}`,
  ].join('\n')
}

/** Render items as paste-ready blocks, never splitting one across two. */
export function formatBriefing(
  items: DigestItem[],
  chunkSize = BRIEF_CHUNK,
  prompt = BRIEF_PROMPT
): string[] {
  const blocks: string[] = []
  for (let start = 0; start < items.length; start += chunkSize) {
    const batch = items.slice(start, start + chunkSize)
    blocks.push([prompt, '', ...batch.map((item) => `${itemBlock(item)}\n`)].join('\n').trim())
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
  chunkSize = BRIEF_CHUNK,
  prompt = BRIEF_PROMPT
): BriefingEntry[] {
  const usable = items.filter((item) => Boolean(item.ref))

  return groupItems(usable, grouping, topicOrder).map((group) => {
    const blocks = formatBriefing(group.items, chunkSize, prompt)
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

/**
 * The finished summaries, grouped, for reading rather than summarising.
 *
 * A briefing asks an AI to summarise from the teaser and forbids it the
 * links, so a briefing handed to an AI "to read" gave it nothing but
 * headlines and links it was told not to open. Once the local model (or a
 * pasted reply) has written the summaries, this is the file to hand over:
 * each item's summary sits in the text, labelled with who wrote it, beside
 * the link a person opens. An item not yet summarised says so and carries
 * its teaser, never an invented summary.
 */
export function buildReadingFiles(
  items: DigestItem[],
  grouping: Grouping,
  topicOrder: string[],
  origin: (source?: string | null) => string
): BriefingEntry[] {
  return groupItems(items, grouping, topicOrder).map((group) => {
    const lines = [`# ${group.label}`, '']
    group.items.forEach((item) => {
      lines.push(
        `## [${item.flag}] ${item.title}`,
        `${item.source_name || '(unknown source)'} · ${(item.created_at || '').slice(0, 10) || '(no date)'} · ${item.topic || FALLBACK_TOPIC}`,
        '',
        item.ai_summary
          ? `${origin(item.ai_source)}: ${item.ai_summary}`
          : `Not summarised yet. Publisher's teaser: ${item.teaser || '(none)'}`,
        '',
        `Link: ${item.link}`,
        ''
      )
    })
    return {
      name: `${group.name}.md`,
      label: group.label,
      text: lines.join('\n'),
      items: group.items.length,
      pastes: 1,
    }
  })
}
