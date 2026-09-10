import { createClient, type SupabaseClient } from '@supabase/supabase-js'

// Created lazily: building the client at module scope crashes `next build`
// when the env vars are absent, because Next evaluates route modules to
// collect page data. Deferring it turns that into a clear runtime error.
let client: SupabaseClient | null = null

function getSupabase() {
  if (!client) {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL
    const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    if (!url || !anonKey) {
      throw new Error(
        'Supabase is not configured. Copy web/.env.local.example to web/.env.local and set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.'
      )
    }
    client = createClient(url, anonKey)
  }
  return client
}

export type Item = {
  id: string
  title: string
  teaser: string | null
  link: string
  source_name: string
  flag: 'ACT' | 'KNOW' | 'NOTE'
  is_read: boolean
  created_at: string
  ai_summary: string | null
  feed_guid: string | null
}

export async function getItems(options?: {
  flag?: string
  after?: string
  before?: string
  source?: string
  limit?: number
  offset?: number
}) {
  let query = getSupabase().from('items').select('*')

  if (options?.flag) {
    query = query.eq('flag', options.flag)
  }
  if (options?.source) {
    query = query.eq('source_name', options.source)
  }
  if (options?.after) {
    query = query.gte('created_at', options.after)
  }
  if (options?.before) {
    query = query.lte('created_at', options.before)
  }

  query = query.order('created_at', { ascending: false })

  if (options?.limit) {
    query = query.limit(options.limit)
  }
  if (options?.offset) {
    query = query.range(options.offset, (options.offset + (options.limit || 20)) - 1)
  }

  const { data, error } = await query

  if (error) throw error
  return data as Item[]
}

export async function markItemAsRead(id: string, isRead: boolean) {
  const { error } = await getSupabase()
    .from('items')
    .update({ is_read: isRead, updated_at: new Date().toISOString() })
    .eq('id', id)

  if (error) throw error
}

export async function markMultipleAsRead(ids: string[], isRead: boolean) {
  const { error } = await getSupabase()
    .from('items')
    .update({ is_read: isRead, updated_at: new Date().toISOString() })
    .in('id', ids)

  if (error) throw error
}

export async function searchItems(query: string, options?: { flag?: string; limit?: number }) {
  let search = getSupabase()
    .from('items')
    .select('*')
    .or(`title.ilike.%${query}%,teaser.ilike.%${query}%`)

  if (options?.flag) {
    search = search.eq('flag', options.flag)
  }

  search = search.order('created_at', { ascending: false })

  if (options?.limit) {
    search = search.limit(options.limit)
  }

  const { data, error } = await search

  if (error) throw error
  return data as Item[]
}

export async function getStats() {
  const { data: items, error } = await getSupabase().from('items').select('flag, is_read')

  if (error) throw error

  const stats = {
    total: items?.length || 0,
    unread: items?.filter(i => !i.is_read).length || 0,
    act: items?.filter(i => i.flag === 'ACT').length || 0,
    know: items?.filter(i => i.flag === 'KNOW').length || 0,
    note: items?.filter(i => i.flag === 'NOTE').length || 0,
    unreadAct: items?.filter(i => i.flag === 'ACT' && !i.is_read).length || 0,
  }

  return stats
}
