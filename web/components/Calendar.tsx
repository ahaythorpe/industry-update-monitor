'use client'

import { DigestItem } from '@/lib/digest'
import type { GlossaryEntry } from '@/lib/glossary'
import { Story } from '@/components/CategoryBoard'
import { formatDay, toDayKey } from '@/lib/utils'

interface CalendarProps {
  items: DigestItem[]
  selectedDate: string | null
  onDateSelect: (date: string) => void
  glossary: GlossaryEntry[]
  readIds: Set<string>
  onToggleRead: (id: string) => void
}

const FLAG_COLOUR: Record<string, string> = {
  ACT: 'bg-red-600',
  KNOW: 'bg-orange-600',
  NOTE: 'bg-green-600',
}

export function Calendar({ items, selectedDate, onDateSelect, glossary, readIds, onToggleRead }: CalendarProps) {
  // Only days that actually carry an item. Walking every calendar day in the
  // range printed 30 or 365 empty rows and buried the days with news in them.
  const itemsByDate = new Map<string, DigestItem[]>()
  items.forEach((item) => {
    const key = toDayKey(item.created_at)
    if (!key) return
    if (!itemsByDate.has(key)) itemsByDate.set(key, [])
    itemsByDate.get(key)!.push(item)
  })

  const days = Array.from(itemsByDate.keys()).sort().reverse()

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-white">Timeline</h2>
        {selectedDate ? (
          <button
            onClick={() => onDateSelect('')}
            className="rounded-full border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-300 hover:border-slate-500"
          >
            Clear day filter
          </button>
        ) : null}
      </div>

      <div className="space-y-3">
        {days.length > 0 ? (
          days.map((dayKey) => {
            const dayItems = itemsByDate.get(dayKey) || []
            const isSelected = selectedDate === dayKey

            // A day opens in place to show its stories; tapping it again closes it.
            return (
              <div key={dayKey}>
              <button
                aria-expanded={isSelected}
                onClick={() => onDateSelect(isSelected ? '' : dayKey)}
                className={`w-full text-left transition-all ${
                  isSelected
                    ? 'border-sky-500 bg-sky-500/10 ring-1 ring-sky-500/30'
                    : 'border-slate-700 hover:border-slate-600 hover:bg-slate-800/50'
                } rounded-2xl border px-4 py-3`}
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1">
                    <div className="font-semibold text-white">{formatDay(dayKey)}</div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {dayItems.map((item) => (
                        <span
                          key={item.id}
                          title={item.title}
                          className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold text-white ${
                            FLAG_COLOUR[item.flag] || 'bg-slate-600'
                          }`}
                        >
                          {item.flag[0]}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="text-sm font-medium text-slate-400">
                    {dayItems.length} item{dayItems.length !== 1 ? 's' : ''} {isSelected ? '▴' : '▾'}
                  </div>
                </div>
              </button>
              {isSelected ? (
                <div className="mt-3 space-y-3 pl-2">
                  {dayItems.map((item) => (
                    <Story
                      key={item.id}
                      item={item}
                      glossary={glossary}
                      isRead={readIds.has(item.id)}
                      onToggleRead={() => onToggleRead(item.id)}
                    />
                  ))}
                </div>
              ) : null}
              </div>
            )
          })
        ) : (
          <div className="rounded-2xl border border-slate-700 bg-slate-800/30 p-4 text-center text-slate-400">
            No items match the current filters
          </div>
        )}
      </div>
    </div>
  )
}
