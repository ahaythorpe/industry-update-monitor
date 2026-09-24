import Dashboard from './dashboard'
import { HOSTED, loadDigest, loadGlossary } from '@/lib/digest-server'

// Read the digest on every request rather than at build time, so re-running
// `python src/monitor.py --json` shows up on the next reload.
export const dynamic = 'force-dynamic'

export default function Home() {
  const digest = loadDigest()
  return (
    <Dashboard
      items={digest.items}
      sources={digest.sources}
      topics={digest.topics}
      generatedAt={digest.generatedAt}
      glossary={loadGlossary()}
      hosted={HOSTED}
    />
  )
}
