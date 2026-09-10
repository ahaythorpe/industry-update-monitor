import { type Flag } from '@/lib/digest'
import { loadDigest } from '@/lib/digest-server'
import { formatWhatsappDigest } from '@/lib/whatsapp'

const FLAGS: Flag[] = ['ACT', 'KNOW', 'NOTE']

export async function POST(request: Request) {
  try {
    const { phoneNumber, selectedFlag, perFlagLimit } = await request.json()

    if (!phoneNumber || typeof phoneNumber !== 'string') {
      return Response.json({ error: 'Phone number required' }, { status: 400 })
    }
    // Twilio needs E.164. Rejecting here beats a 400 from Twilio the user
    // cannot see.
    if (!/^\+[1-9]\d{7,14}$/.test(phoneNumber.trim())) {
      return Response.json(
        { error: 'Use international format, e.g. +61412345678' },
        { status: 400 }
      )
    }

    const digestItems = loadDigest().items
    const flag = FLAGS.includes(selectedFlag) ? (selectedFlag as Flag) : null
    const items = flag ? digestItems.filter((item) => item.flag === flag) : digestItems
    const bodies = formatWhatsappDigest(items, typeof perFlagLimit === 'number' ? perFlagLimit : 6)

    const accountSid = process.env.TWILIO_ACCOUNT_SID
    const authToken = process.env.TWILIO_AUTH_TOKEN
    const whatsappNumber = process.env.TWILIO_WHATSAPP_NUMBER

    if (!accountSid || !authToken || !whatsappNumber) {
      // Nothing is sent and nothing pretends to have been sent: the caller gets
      // the exact bodies, which is what preview mode means in the Python sender.
      return Response.json({
        success: true,
        sent: false,
        parts: bodies.length,
        message:
          'Twilio is not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_NUMBER to send.',
        preview: bodies.join('\n\n— — —\n\n'),
      })
    }

    // Sent in order, one request per part: WhatsApp caps a body at 1600 chars.
    for (const body of bodies) {
      const form = new URLSearchParams({
        From: `whatsapp:${whatsappNumber}`,
        To: `whatsapp:${phoneNumber.trim()}`,
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
