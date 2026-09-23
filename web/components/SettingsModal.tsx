'use client'

import { useEffect } from 'react'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  // Escape closes it too. The panel is taller than a laptop screen, and
  // before it scrolled, both close buttons sat off-screen with no way out.
  useEffect(() => {
    if (!isOpen) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4 backdrop-blur-sm sm:items-center"
    >
      <div
        onClick={(event) => event.stopPropagation()}
        className="relative my-4 max-h-[calc(100vh-2rem)] w-full max-w-2xl overflow-y-auto rounded-3xl border border-slate-700 bg-slate-900 p-8 shadow-2xl"
      >
        <div className="sticky -top-8 z-10 -mx-8 -mt-8 mb-6 flex items-center justify-between rounded-t-3xl bg-slate-900 px-8 pt-8 pb-4">
          <h2 className="text-2xl font-bold text-white">⚙️ Settings</h2>
          <button
            onClick={onClose}
            aria-label="Close settings"
            className="rounded-lg px-3 py-1 text-xl text-slate-400 hover:bg-slate-800 hover:text-slate-200"
          >
            ✕
          </button>
        </div>

        <div className="space-y-8">
          {/* Feed Eligibility */}
          <div>
            <h3 className="mb-4 text-lg font-semibold text-white">📰 Feed Eligibility for Automation</h3>
            <div className="space-y-3 rounded-2xl border border-slate-700 bg-slate-800/50 p-5">
              <div>
                <div className="flex items-center gap-2">
                  <span className="inline-block h-2 w-2 rounded-full bg-green-500"></span>
                  <span className="font-medium text-green-300">✓ Eligible (Free)</span>
                </div>
                <ul className="mt-2 ml-4 space-y-1 text-sm text-slate-300">
                  <li>• Public RSS feeds (no authentication required)</li>
                  <li>• Newsletter subscriptions you already receive (needs the Gmail setup in SETUP.md Part 4 — not connected yet)</li>
                  <li>• Official government/regulator publications</li>
                  <li>• Public news feeds with open API access</li>
                </ul>
              </div>
              <hr className="border-slate-600" />
              <div>
                <div className="flex items-center gap-2">
                  <span className="inline-block h-2 w-2 rounded-full bg-red-500"></span>
                  <span className="font-medium text-red-300">✗ Not Eligible (Paywalled)</span>
                </div>
                <ul className="mt-2 ml-4 space-y-1 text-sm text-slate-300">
                  <li>• Subscription-only content (e.g., FT, WSJ)</li>
                  <li>• Login-required resources</li>
                  <li>• Paid API access only</li>
                  <li>• Content behind paywalls</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Email Digest */}
          <div>
            <h3 className="mb-4 text-lg font-semibold text-white">📧 Email Digest Setup</h3>
            <div className="space-y-3 rounded-2xl border border-slate-700 bg-slate-800/50 p-5">
              <p className="text-sm text-slate-300">
                The dashboard never sends mail — sending lives with the credentials, in the Python monitor. Read the
                email body here first, then send it from the CLI.
              </p>
              <ol className="ml-4 space-y-1 text-sm text-slate-300">
                <li>1. Set SMTP_* (or EMAIL_ADDRESS / EMAIL_PASSWORD) in <code>.env</code></li>
                <li>2. Run <code>python src/monitor.py --json</code> to refresh this digest</li>
                <li>3. Run <code>python src/monitor.py --email</code> to send it</li>
              </ol>
              <a
                href="/api/email/preview"
                target="_blank"
                rel="noreferrer"
                className="inline-block rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-600"
              >
                Preview the email body
              </a>
              <p className="text-xs text-slate-400">🔒 Credentials stay in .env, which is git-ignored.</p>
            </div>
          </div>

          {/* WhatsApp Digest */}
          <div>
            <h3 className="mb-4 text-lg font-semibold text-white">📱 WhatsApp Digest Setup</h3>
            <div className="space-y-3 rounded-2xl border border-slate-700 bg-slate-800/50 p-5">
              <p className="text-sm text-slate-300">
                Get instant digests on WhatsApp. Already available on the dashboard.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    onClose()
                    document.getElementById('whatsapp-scroll')?.scrollIntoView({ behavior: 'smooth' })
                  }}
                  className="flex-1 rounded-lg bg-green-600 px-4 py-2 font-medium text-white hover:bg-green-700"
                >
                  Go to WhatsApp Sender
                </button>
              </div>
              <p className="text-xs text-slate-400">
                ℹ️ Works in demo mode (shows preview) or with Twilio credentials configured
              </p>
            </div>
          </div>

          {/* Schedule */}
          <div>
            <h3 className="mb-4 text-lg font-semibold text-white">🕐 Automation Schedule</h3>
            <div className="space-y-3 rounded-2xl border border-slate-700 bg-slate-800/50 p-5">
              <p className="text-sm text-slate-300">
                The digest refreshes itself every Monday at 7am on your Mac (see
                <code> output/weekly-run.log</code>). Once the summaries are written it emails the newsletter to you — your own
                address only. It never sends WhatsApp on its own.
              </p>
            </div>
          </div>

          {/* Close */}
          <div className="mt-8 flex justify-end">
            <button
              onClick={onClose}
              className="rounded-lg bg-slate-700 px-6 py-2 font-medium text-white hover:bg-slate-600"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
