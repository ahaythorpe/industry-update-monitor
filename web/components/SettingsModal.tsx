'use client'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-3xl border border-slate-700 bg-slate-900 p-8 shadow-2xl">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white">⚙️ Settings</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
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
                  <li>• Newsletter subscriptions you already receive</li>
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
                Currently manual triggers. To enable automatic scheduling:
              </p>
              <ul className="ml-4 space-y-1 text-sm text-slate-300">
                <li>1. Deploy backend service (Python monitor)</li>
                <li>2. Configure cron jobs for email/WhatsApp sends</li>
                <li>3. Set up database for tracking sent items</li>
              </ul>
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
