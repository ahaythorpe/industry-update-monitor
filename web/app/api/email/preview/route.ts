import { readFileSync } from 'node:fs'
import path from 'node:path'
import { NextRequest } from 'next/server'
import { type DigestItem, type Flag } from '@/lib/digest'
import { loadDigest } from '@/lib/digest-server'
import { formatDay } from '@/lib/utils'

/**
 * Render the digest as the email body, for reading in the browser.
 *
 * The dashboard never sends mail: sending lives in src/email_sender.py behind
 * `python src/monitor.py --email`, where the SMTP credentials are. This route
 * exists so the email path can be proof-read without credentials and without
 * anything leaving the machine.
 */

const FLAG_LABELS: Record<Flag, { heading: string; colour: string }> = {
  ACT: { heading: '🔴 ACT — needs action', colour: '#c0392b' },
  KNOW: { heading: '🟠 KNOW — worth knowing', colour: '#d35400' },
  NOTE: { heading: '🟢 NOTE — background', colour: '#27ae60' },
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function renderItem(item: DigestItem): string {
  const confidence =
    typeof item.confidence === 'number' ? ` · ${Math.round(item.confidence * 100)}% confidence` : ''
  return `
    <div class="item" style="border-left-color:${FLAG_LABELS[item.flag].colour}">
      <h3>${escapeHtml(item.title)}</h3>
      <p>${escapeHtml(item.teaser)}</p>
      <p class="meta">${escapeHtml(item.source_name)}${confidence}</p>
      <a href="${escapeHtml(item.link)}">Read at source</a>
    </div>`
}

// The email exactly as src/email_sender.py builds it, written by
// `python src/monitor.py --from-digest --preview` (the Monday run does this).
// One renderer: the simple page below is only a fallback for when that file
// has not been written yet, or a single urgency is asked for.
const SENT_PREVIEW = path.join(process.cwd(), '..', 'output', 'digest_preview.html')

export function GET(request: NextRequest) {
  const flag = request.nextUrl.searchParams.get('flag') as Flag | null
  if (!flag) {
    try {
      return new Response(readFileSync(SENT_PREVIEW, 'utf8'), {
        headers: { 'content-type': 'text/html; charset=utf-8' },
      })
    } catch {
      // Not written yet: fall through to the simple page.
    }
  }
  const { items: digestItems, generatedAt } = loadDigest()
  const items = flag ? digestItems.filter((item) => item.flag === flag) : digestItems

  const sections = (Object.keys(FLAG_LABELS) as Flag[])
    .map((key) => {
      const group = items.filter((item) => item.flag === key)
      if (!group.length) return ''
      return `<h2>${FLAG_LABELS[key].heading} (${group.length})</h2>${group.map(renderItem).join('')}`
    })
    .join('')

  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Digest email preview</title>
<style>
 body { font-family: Arial, Helvetica, sans-serif; line-height: 1.6; color: #333; background: #fff; }
 .container { max-width: 640px; margin: 0 auto; padding: 24px; }
 h1 { color: #1a1a1a; border-bottom: 3px solid #0066cc; padding-bottom: 10px; }
 h2 { margin-top: 32px; font-size: 1.05em; }
 h3 { margin: 0 0 6px; font-size: 1em; }
 .item { margin-bottom: 18px; padding: 14px; border-left: 4px solid #ddd; background: #f9f9f9; }
 .meta { color: #666; font-size: 0.85em; margin: 6px 0; }
 .footer { margin-top: 32px; color: #666; font-size: 0.85em; border-top: 1px solid #eee; padding-top: 12px; }
</style></head><body><div class="container">
 <h1>Industry Update Monitor — digest</h1>
 <p class="meta">${items.length} item${items.length === 1 ? '' : 's'} · collected ${escapeHtml(
   formatDay(generatedAt)
 )}</p>
 ${sections || '<p>Nothing cleared the filters this week.</p>'}
 <p class="footer">Teasers and links only — never full article text. Preview rendered locally;
 sending is done by <code>python src/monitor.py --email</code>.</p>
</div></body></html>`

  return new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8' } })
}
