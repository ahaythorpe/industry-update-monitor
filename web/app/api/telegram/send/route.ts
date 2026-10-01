import { type Flag } from '@/lib/digest'
import { loadDigest, loadGlossary } from '@/lib/digest-server'
import { explainTelegramError, formatTelegramDigest } from '@/lib/telegram'

const FLAGS: Flag[] = ['ACT', 'KNOW', 'NOTE']

// This endpoint sends to one chat only: TELEGRAM_CHAT_ID from the server
// environment — your own chat with your own bot. It deliberately ignores any
// recipient (chat_id, to, recipient…) in the request body.
//
// Why: the route has no authentication and no rate limit, and it is built from
// a public repository. Taking the recipient from the body would make it a
// send-to-anyone API for whoever found the URL, speaking as your bot. Reading
// the recipient from the environment means the worst a stranger can do is send
// this digest to the owner's own chat. The same rule protected the WhatsApp
// route it replaces (chosen 17 Sep 2026 — option A; see HANDOVER.md). Do not
// reintroduce a body-supplied recipient without replacing this protection.
//
// TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID belong in web/.env.local on your own
// Mac only. Never put them into Vercel: that would make this button live on a
// public URL. Without them the route returns a preview and sends nothing.
export async function POST(request: Request) {
  const token = process.env.TELEGRAM_BOT_TOKEN?.trim()
  try {
    const { selectedFlag } = await request.json().catch(() => ({}))

    const chatId = process.env.TELEGRAM_CHAT_ID?.trim()

    const digestItems = loadDigest().items
    const flag = FLAGS.includes(selectedFlag) ? (selectedFlag as Flag) : null
    // One message, the same one `python src/monitor.py --telegram` sends.
    const messages = [
      formatTelegramDigest(digestItems, {
        focus: flag,
        dashboard: process.env.DASHBOARD_URL?.trim() || null,
        glossary: loadGlossary(),
      }),
    ]

    if (!token || !chatId) {
      // Nothing is sent and nothing pretends to have been sent: the caller gets
      // the exact messages, which is what preview mode means in the Python sender.
      return Response.json({
        success: true,
        sent: false,
        parts: messages.length,
        message: 'Telegram is not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in web/.env.local to send.',
        preview: messages.join('\n\n— — —\n\n'),
      })
    }

    // Sent in order, one request per part: Telegram caps a message at 4096 chars.
    for (let index = 0; index < messages.length; index++) {
      const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: chatId,
          text: messages[index],
          parse_mode: 'HTML',
          disable_web_page_preview: true,
        }),
      })
      const reply = await response.json().catch(() => ({}))

      if (!response.ok || !reply.ok) {
        // Telegram's description never contains the token; the URL does, so it
        // is never logged.
        console.error('Telegram refused message', index + 1, 'of', messages.length, response.status, reply.description)
        const sentSoFar = index ? ` ${index} of ${messages.length} parts had already arrived.` : ''
        return Response.json(
          { error: `${explainTelegramError(reply.description, response.status)}${sentSoFar}` },
          { status: 502 }
        )
      }
    }

    return Response.json({
      success: true,
      sent: true,
      parts: messages.length,
      message: 'Digest sent to your Telegram chat.',
    })
  } catch (error) {
    // Scrub the token in case a network error ever echoes the request URL.
    const detail = error instanceof Error ? error.message : String(error)
    console.error('Telegram send error:', token ? detail.split(token).join('•••') : detail)
    return Response.json(
      {
        error:
          'Could not send the digest to Telegram. Check the internet connection and try again; if it keeps happening, the dev server window has the detail.',
      },
      { status: 500 }
    )
  }
}
