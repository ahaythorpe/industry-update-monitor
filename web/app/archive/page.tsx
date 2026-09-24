import Link from 'next/link'
import { listWeeks } from '@/lib/digest-server'

export const metadata = { title: 'Past weeks · This week in Australian advice' }

function weekLabel(week: string): string {
  const date = new Date(`${week}T00:00:00`)
  return date.toLocaleDateString('en-AU', { day: 'numeric', month: 'long', year: 'numeric' })
}

export default function Archive() {
  const weeks = listWeeks()
  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100">
      <div className="mx-auto max-w-3xl">
        <Link href="/" className="text-sm text-sky-300 hover:underline">
          ← This week
        </Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-white">Past weeks</h1>
        <p className="mt-3 text-slate-300">
          Every week the monitor has published, newest first. Each one is kept as it was sent.
        </p>
        {weeks.length ? (
          <ul className="mt-8 space-y-3">
            {weeks.map((entry) => (
              <li key={entry.week}>
                <Link
                  href={`/week/${entry.week}`}
                  className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-900/60 p-5 hover:border-sky-700"
                >
                  <span className="text-lg font-semibold text-white">Week of {weekLabel(entry.week)}</span>
                  <span className="text-sm text-slate-400">
                    {entry.stories} stories · 🔴 {entry.actNow} act now
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-8 text-slate-400">No past weeks saved yet.</p>
        )}
      </div>
    </main>
  )
}
