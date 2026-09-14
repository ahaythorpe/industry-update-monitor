'use client'

/**
 * What the tool does instead of scraping, and how you can check.
 *
 * Shown from the download panel, because that is the moment content leaves
 * the tool and goes into an AI window — the point at which "where did this
 * text come from?" actually matters.
 *
 * Everything here is checkable in the repo rather than a promise. The file
 * and line references are the point: the claim is that the capability does
 * not exist, not that it exists and is unused.
 */

interface PaywallModalProps {
  isOpen: boolean
  onClose: () => void
}

export function PaywallModal({ isOpen, onClose }: PaywallModalProps) {
  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-3xl border border-slate-700 bg-slate-900 p-8 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-6 flex items-start justify-between gap-4">
          <h2 className="text-2xl font-bold text-white">Why this never scrapes paid sources</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="shrink-0 rounded-full px-2 text-slate-400 hover:text-slate-200"
          >
            ✕
          </button>
        </div>

        <p className="text-sm text-slate-300">
          Not a policy it follows — a capability it does not have. There is no code here that can
          read an article, and no credentials for it to log in with.
        </p>

        <div className="mt-6 space-y-5 text-sm">
          <section className="rounded-2xl border border-slate-700 bg-slate-800/50 p-5">
            <h3 className="font-semibold text-white">It only reads what publishers give away</h3>
            <p className="mt-2 text-slate-300">
              Every item comes from an RSS feed the publisher chose to publish, or a newsletter that
              arrived in your own inbox. What goes into a briefing is two fields from that feed —
              the <strong className="text-white">headline</strong> and the{' '}
              <strong className="text-white">teaser the publisher wrote for the public</strong> —
              plus the link.
            </p>
            <p className="mt-2 text-slate-400">
              The article URL is stored so you can click it. It is never fetched to read.
            </p>
          </section>

          <section className="rounded-2xl border border-slate-700 bg-slate-800/50 p-5">
            <h3 className="font-semibold text-white">Three places touch the network. That is all</h3>
            <ul className="mt-2 space-y-2 text-slate-300">
              <li>
                <span className="text-white">1. Fetching a feed</span> — reads the RSS file, which is
                public by design.
              </li>
              <li>
                <span className="text-white">2. Checking a link still works</span> — asks the URL
                whether it resolves, then throws the response away.{' '}
                <span className="text-slate-400">
                  It never reads the page body; that is the difference between a link check and a
                  scrape.
                </span>
              </li>
              <li>
                <span className="text-white">3. Sending your own digest</span> — to your email or
                WhatsApp, nothing to do with publishers.
              </li>
            </ul>
            <p className="mt-3 text-slate-400">
              There is no fourth. Search the code for a request to an article page and you will not
              find one.
            </p>
          </section>

          <section className="rounded-2xl border border-slate-700 bg-slate-800/50 p-5">
            <h3 className="font-semibold text-white">There is nothing to log in with</h3>
            <p className="mt-2 text-slate-300">
              No publisher account, no password, no cookie, no session anywhere in the project. A
              paywall cannot be passed by something that never signs in.
            </p>
          </section>

          <section className="rounded-2xl border border-slate-700 bg-slate-800/50 p-5">
            <h3 className="font-semibold text-white">The AI is told the same thing</h3>
            <p className="mt-2 text-slate-300">
              Every block you paste carries the instruction{' '}
              <em className="text-slate-200">
                &ldquo;summarise ONLY from the teaser given&rdquo;
              </em>{' '}
              and{' '}
              <em className="text-slate-200">
                &ldquo;do not attempt to access anything beyond the text provided&rdquo;
              </em>
              . If a teaser is too thin to summarise, the correct answer is{' '}
              <span className="text-white">&ldquo;thin — open source&rdquo;</span> — admit it rather
              than invent something.
            </p>
          </section>

          <section className="rounded-2xl border border-emerald-900/60 bg-emerald-950/20 p-5">
            <h3 className="font-semibold text-white">What you can summarise in full</h3>
            <p className="mt-2 text-slate-300">
              Regulator documents — ASIC reports and media releases, Treasury consultations, AFCA
              determinations, ABS releases — are free public documents. Upload those whole. You save
              them yourself: no part of this tool downloads a document, and that is worth keeping
              literally true.
            </p>
          </section>
        </div>

        <p className="mt-6 text-xs text-slate-500">
          The full rules are in SAFEGUARDS.md section A, and the honest caveat about the link check
          is written up in INTEGRATIONS.md rather than left for you to find.
        </p>

        <button
          onClick={onClose}
          className="mt-6 w-full rounded-xl bg-slate-800 px-5 py-3 text-sm font-semibold text-slate-200 hover:bg-slate-700"
        >
          Close
        </button>
      </div>
    </div>
  )
}
