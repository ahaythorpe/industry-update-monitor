import { notFound } from 'next/navigation'
import Dashboard from '../../dashboard'
import { listWeeks, loadGlossary, loadWeek } from '@/lib/digest-server'

// One static page per saved week, built when the site is deployed.
export const dynamicParams = false

export function generateStaticParams() {
  return listWeeks().map(({ week }) => ({ week }))
}

export default async function Week({ params }: { params: Promise<{ week: string }> }) {
  const { week } = await params
  const digest = loadWeek(week)
  if (!digest) notFound()
  return (
    <Dashboard
      items={digest.items}
      sources={digest.sources}
      topics={digest.topics}
      generatedAt={digest.generatedAt}
      glossary={loadGlossary()}
      // A past week is for reading: none of the owner's sending or settings.
      hosted
      week={week}
    />
  )
}
