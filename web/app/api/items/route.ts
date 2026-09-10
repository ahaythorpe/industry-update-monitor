import { NextRequest, NextResponse } from 'next/server'
import { getItems, getStats } from '@/lib/digest'
import { loadDigest } from '@/lib/digest-server'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const flag = searchParams.get('flag') || undefined
    const source = searchParams.get('source') || undefined
    const limit = searchParams.get('limit') ? parseInt(searchParams.get('limit')!) : 50
    const query = searchParams.get('query') || undefined
    const exactness = searchParams.get('exactness') as 'all' | 'exact' | 'fallback' | 'broad' | null

    const { items: all } = loadDigest()
    const items = getItems(all, {
      flag,
      source,
      limit,
      query,
      exactness: exactness || 'exact',
    })

    return NextResponse.json({ items, stats: getStats(all) })
  } catch (error) {
    console.error('GET /api/items:', error)
    return NextResponse.json(
      { error: 'Failed to fetch items' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { ids, is_read } = body

    if (!ids || typeof is_read !== 'boolean') {
      return NextResponse.json(
        { error: 'Missing ids or is_read' },
        { status: 400 }
      )
    }

    return NextResponse.json({ success: true, updated: ids.length, is_read })
  } catch (error) {
    console.error('POST /api/items:', error)
    return NextResponse.json(
      { error: 'Failed to update items' },
      { status: 500 }
    )
  }
}
