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
  // Both are needed to send: the token says which bot, the chat ID says which
  // chat. A token alone is not live, so it is reported as half-done.
  const telegramToken = Boolean(process.env.TELEGRAM_BOT_TOKEN?.trim())
  const telegramChat = Boolean(process.env.TELEGRAM_CHAT_ID?.trim())
  const telegramConfigured = telegramToken && telegramChat

  return NextResponse.json({
    digest: {
      generated_at: digest.generatedAt,
      items: digest.items.length,
      sources: digest.sources.length,
      // false means the file could not be read and this is the copy bundled
      // at build time — a stale digest, honestly labelled.
      live: digest.live,
    },
    telegram: {
      configured: telegramConfigured,
      detail: telegramConfigured
        ? 'Bot token and chat ID found — sending to your own Telegram chat is live. Free, no per-message charge.'
        : telegramToken
          ? 'Bot token found but no chat ID yet. Press Start on the bot in Telegram, then ask Claude to find the chat ID. Until then the button shows the exact message instead of sending.'
          : 'Not set up. The button shows the exact message instead of sending, so it can be proof-read. Set up: SETUP.md Part 5.',
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
