import { type Flag } from '@/lib/digest'
import { loadDigest } from '@/lib/digest-server'
import { formatWhatsappDigest } from '@/lib/whatsapp'

const FLAGS: Flag[] = ['ACT', 'KNOW', 'NOTE']

// This endpoint sends to one number only: WHATSAPP_TO from the server
// environment. It deliberately ignores any recipient in the request body.
//
// Why: the route has no authentication and no rate limit, and it is deployed
// from a public repository. Taking the recipient from the body would make it a
// send-to-anyone API for whoever found the URL — they could aim the Twilio
// balance at their own phone. Reading the recipient from the environment means
// the worst a stranger can do is send this digest to the owner's own phone.
//
// Chosen 17 Sep 2026 — option A; see the WhatsApp section of HANDOVER.md. Do not
// reintroduce a body-supplied recipient without replacing this protection.
export async function POST(request: Request) {
  try {
    const { selectedFlag, perFlagLimit } = await request.json().catch(() => ({}))

    const recipient = process.env.WHATSAPP_TO?.trim()

    const digestItems = loadDigest().items
    const flag = FLAGS.includes(selectedFlag) ? (selectedFlag as Flag) : null
    const items = flag ? digestItems.filter((item) => item.flag === flag) : digestItems
    const bodies = formatWhatsappDigest(items, typeof perFlagLimit === 'number' ? perFlagLimit : 6)

    const accountSid = process.env.TWILIO_ACCOUNT_SID
    const authToken = process.env.TWILIO_AUTH_TOKEN
    const whatsappNumber = process.env.TWILIO_WHATSAPP_NUMBER

    if (!accountSid || !authToken || !whatsappNumber || !recipient) {
      // Nothing is sent and nothing pretends to have been sent: the caller gets
      // the exact bodies, which is what preview mode means in the Python sender.
      return Response.json({
        success: true,
        sent: false,
        parts: bodies.length,
        message:
          'Twilio is not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER and WHATSAPP_TO to send.',
        preview: bodies.join('\n\n— — —\n\n'),
      })
    }

    // Sent in order, one request per part: WhatsApp caps a body at 1600 chars.
    for (const body of bodies) {
      const form = new URLSearchParams({
        From: `whatsapp:${whatsappNumber}`,
        To: `whatsapp:${recipient}`,
        Body: body,
      })

      const response = await fetch(
        `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Messages.json`,
        {
          method: 'POST',
          headers: {
            Authorization: 'Basic ' + Buffer.from(`${accountSid}:${authToken}`).toString('base64'),
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: form,
        }
      )

      if (!response.ok) {
        const detail = await response.text()
        console.error('Twilio rejected the message:', response.status, detail)
        return Response.json(
          { error: `Twilio rejected the message (HTTP ${response.status})` },
          { status: 502 }
        )
      }
    }

    return Response.json({
      success: true,
      sent: true,
      parts: bodies.length,
      message: 'Digest sent to WhatsApp.',
    })
  } catch (error) {
    console.error('WhatsApp send error:', error)
    return Response.json({ error: 'Failed to send digest' }, { status: 500 })
  }
}
