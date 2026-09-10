export function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 60) {
    return `${diffMins}m ago`
  } else if (diffHours < 24) {
    return `${diffHours}h ago`
  } else if (diffDays < 7) {
    return `${diffDays}d ago`
  } else {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }
}

export function formatTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

// Rendered on the server and again in the browser, so the format must not
// depend on the machine's locale or time zone: an implicit toLocaleDateString()
// produced "09/09/2026" on the server and "9/9/2026" in Chrome, and React threw
// the whole tree away and re-rendered it as a hydration mismatch.
const DAY_FORMAT = new Intl.DateTimeFormat('en-AU', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
})

export function formatDay(dateString: string): string {
  const date = new Date(dateString)
  return Number.isNaN(date.getTime()) ? '' : DAY_FORMAT.format(date)
}

export function toDayKey(dateString: string): string {
  const date = new Date(dateString)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString().split('T')[0]
}
