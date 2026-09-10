import { NextRequest, NextResponse } from 'next/server'
import { getItems } from '@/lib/digest'
import { loadDigest } from '@/lib/digest-server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { query, flag, limit } = body

    if (!query || query.trim().length === 0) {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      )
    }

    const items = getItems(loadDigest().items, {
      flag,
      limit: limit || 50,
      query,
    })

    return NextResponse.json({ items })
  } catch (error) {
    console.error('POST /api/search:', error)
    return NextResponse.json(
      { error: 'Failed to search items' },
      { status: 500 }
    )
  }
}
