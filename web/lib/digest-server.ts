import { readFileSync } from 'node:fs'
import path from 'node:path'
import bundled from './digest.json'
import { normalizeIncomingItem, type DigestItem, type DigestSource } from './digest'
import type { GlossaryEntry } from './glossary'

/**
 * Load the digest at request time, not at build time.
 *
 * `import digest from './digest.json'` bakes whichever copy existed when
 * `next build` ran, so re-running `python src/monitor.py --json` against a
 * built app changed nothing — the README told you to refresh a digest the
 * dashboard could not see. Reading the file per request fixes that.
 *
 * The bundled import stays as the fallback: on a host with a read-only or
 * traced filesystem (Vercel), the file may not be there to read, and a stale
 * digest beats a crash. `generated_at` always says which one you are looking
 * at.
 */

export type DigestPayload = {
  generatedAt: string
  items: DigestItem[]
  sources: DigestSource[]
  topics: string[]
  live: boolean
}

type RawPayload = {
  generated_at?: string
  topics?: string[]
  sources?: DigestSource[]
  items?: Parameters<typeof normalizeIncomingItem>[0][]
}

const DIGEST_PATH = path.join(process.cwd(), 'lib', 'digest.json')

function shape(raw: RawPayload, live: boolean): DigestPayload {
  return {
    generatedAt: raw.generated_at || '',
    sources: raw.sources || [],
    // A digest written before the monitor published its labels falls back to
    // whatever categories its own items carry.
    topics: raw.topics?.length
      ? raw.topics
      : Array.from(new Set((raw.items || []).map((item) => item.topic).filter(Boolean) as string[])),
    items: (raw.items || []).map((item) => normalizeIncomingItem(item)),
    live,
  }
}

export function loadDigest(): DigestPayload {
  try {
    return shape(JSON.parse(readFileSync(DIGEST_PATH, 'utf8')) as RawPayload, true)
  } catch {
    return shape(bundled as RawPayload, false)
  }
}

const GLOSSARY_PATH = path.join(process.cwd(), '..', 'data', 'glossary.json')

/**
 * The hand-written glossary the monitor uses, read per request like the
 * digest: data/glossary.json on this Mac, else the copy export_json puts in
 * the digest. Missing or unreadable is not an error: the dashboard just shows
 * no term explanations.
 */
export function loadGlossary(): GlossaryEntry[] {
  const usable = (terms?: GlossaryEntry[]) => (terms || []).filter((entry) => entry.term && entry.means)
  try {
    return usable((JSON.parse(readFileSync(GLOSSARY_PATH, 'utf8')) as { terms?: GlossaryEntry[] }).terms)
  } catch {
    // Deployed, data/ is not there: use the copy the digest carries.
    try {
      return usable((JSON.parse(readFileSync(DIGEST_PATH, 'utf8')) as { glossary?: GlossaryEntry[] }).glossary)
    } catch {
      return usable((bundled as { glossary?: GlossaryEntry[] }).glossary)
    }
  }
}
