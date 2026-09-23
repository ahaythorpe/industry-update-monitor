import { NextResponse } from 'next/server'
import { loadDigest } from '@/lib/digest-server'

/**
 * What is actually configured on this deployment.
 *
 * The dashboard used to show three toggles that only flipped a piece of React
 * state, so "Email digest: Enabled" meant nothing. The project rule is that a
 * feature which is not configured must not look live, so the cards now report
 * what the server can really do.
 */
export function GET() {
  const digest = loadDigest()

  const smtpConfigured = Boolean(
    (process.env.SMTP_HOST && process.env.SMTP_PASSWORD) ||
      (process.env.EMAIL_ADDRESS && process.env.EMAIL_PASSWORD)
  )
  const twilioConfigured = Boolean(
    process.env.TWILIO_ACCOUNT_SID &&
      process.env.TWILIO_AUTH_TOKEN &&
      process.env.TWILIO_WHATSAPP_NUMBER
  )

  return NextResponse.json({
    digest: {
      generated_at: digest.generatedAt,
      items: digest.items.length,
      sources: digest.sources.length,
      // false means the file could not be read and this is the copy bundled
      // at build time — a stale digest, honestly labelled.
      live: digest.live,
    },
    whatsapp: {
      configured: twilioConfigured,
      detail: twilioConfigured
        ? 'Twilio credentials found — sending is live.'
        : 'No Twilio credentials. Sending returns the exact message instead, so it can be proof-read for free.',
    },
    email: {
      configured: smtpConfigured,
      detail: smtpConfigured
        ? 'SMTP credentials found. Send with: python src/monitor.py --email'
        : 'No SMTP credentials. Set SMTP_* or EMAIL_ADDRESS/EMAIL_PASSWORD in .env, then send with: python src/monitor.py --email',
    },
    ai: {
      configured: false,
      detail:
        'Not built. Classification is weighted keywords only — no AI, no API key, no per-run cost. Free summaries: --ollama on this machine (SETUP.md Part 2).',
    },
  })
}
