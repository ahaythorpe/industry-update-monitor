# Web Platform Plan: Tracking Dashboard + Supabase

A lightweight web tracking system to replace local digest runs with a persistent, queryable database and browser dashboard. Built on Supabase (free tier) and Next.js on Vercel. Extensible; email and advanced features added later.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ Local Python Worker (existing, refactored)                   │
│ - Reads RSS feeds (Phase 1 logic)                            │
│ - Prioritises by keyword → 🔴/🟠/🟢                         │
│ - Writes NEW items to Supabase (no duplicates)              │
│ - Runs weekly (cron or manual)                              │
└────────────────┬────────────────────────────────────────────┘
                 │ (writes items)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Supabase (free tier)                                        │
│ - items: title, teaser, link, source, flag, read, AI_summary
│ - created_at, updated_at for filtering                      │
│ - All live queries via REST API                             │
└────────────────┬────────────────────────────────────────────┘
                 │ (read items)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Next.js Web App (Vercel)                                    │
│ - Dashboard: view items, filter by flag, mark read          │
│ - Search: query by source, title, date                      │
│ - Summary toggle (NB: the USE_AI switch sketched here        │
│   was never built; see Success Criteria below)              │
│ - No auth yet (personal use)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| **Database** | Supabase (PostgreSQL) | Free tier, JSON API, real-time queries, backup included |
| **Frontend** | Next.js 14 (App Router) | Vercel native, SSR/SSG, API routes for worker auth |
| **Hosting** | Vercel | Free tier, auto-deploys from GitHub |
| **Python worker** | Existing (refactored) | Keep locally; later: serverless function if needed |
| **Worker scheduling** | Manual (cron via crontab) | Free; add GitHub Actions later if needed |

---

## Supabase Schema

### Table: `items`
```sql
CREATE TABLE items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Content
  title TEXT NOT NULL,
  teaser TEXT,
  link TEXT NOT NULL,
  source_name TEXT NOT NULL,  -- e.g. "ASIC", "Financial Standard"
  
  -- Flags
  flag VARCHAR(10) NOT NULL,  -- 'ACT', 'KNOW', 'NOTE'
  
  -- State
  is_read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  
  -- Optional AI (Phase 1B)
  ai_summary TEXT,
  ai_generated_at TIMESTAMPTZ,
  
  -- Dedup
  feed_guid TEXT UNIQUE,  -- RSS guid; prevents duplicates
  
  -- Index for queries
  created_at DESC,
  source_name,
  flag
);
```

### Table: `sources` (metadata, optional)
```sql
CREATE TABLE sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,         -- e.g. "ASIC"
  feed_url TEXT,              -- RSS URL
  category TEXT,              -- 'regulator', 'trade_press', 'bookmark'
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Python Worker Changes

**Existing flow:** Read RSS → collate → prioritise → print digest

**New flow:** Read RSS → collate → prioritise → write to Supabase (skip already-seen)

### Key changes:
1. Add `supabase-py` to `requirements.txt`
2. New function `store_items_to_db()`:
   - Take collated items list
   - For each: check if `feed_guid` exists in DB
   - If new: insert row with flag, teaser, link, source
   - Skip duplicates
3. ~~Keep `USE_AI` logic; when True and key exists, add `ai_summary` to row~~ — there is no
   `USE_AI` logic to keep. `ai_summary` is filled by `--ollama` or `--import-summaries`.

### No breaking changes:
- Existing command-line interface stays
- Can still run `python src/monitor.py` locally (print to stdout + DB)
- ~~`USE_AI` switch works the same~~ — never existed
- Same guardrails apply

---

## Next.js Web App Structure

```
web/
├── app/
│   ├── layout.tsx          (root layout, Supabase client setup)
│   ├── page.tsx            (dashboard homepage)
│   ├── api/
│   │   ├── items/route.ts  (GET items, POST mark-read)
│   │   └── search/route.ts (POST search query)
│   └── components/
│       ├── ItemCard.tsx    (single item display)
│       ├── FilterBar.tsx   (flag filters, date range)
│       ├── SearchBox.tsx   (free text search)
│       └── Dashboard.tsx   (main grid/list)
├── lib/
│   ├── supabase.ts         (client init, queries)
│   └── utils.ts            (format dates, flag colors)
├── public/
├── package.json
└── tsconfig.json
```

---

## API Routes (Next.js)

### `GET /api/items`
Query parameters: `flag`, `after`, `before`, `source`, `limit`
Returns: array of items, newest first
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "ASIC updates AFSL fees",
      "teaser": "...",
      "link": "https://...",
      "flag": "ACT",
      "is_read": false,
      "source_name": "ASIC",
      "created_at": "2026-08-31T10:00:00Z",
      "ai_summary": null
    }
  ],
  "count": 42
}
```

### `POST /api/items`
Mark items as read
```json
{
  "ids": ["uuid1", "uuid2"],
  "is_read": true
}
```

### `POST /api/search`
Free-text search
```json
{
  "query": "super",
  "flag": "ACT",
  "limit": 20
}
```

---

## Dashboard Features (MVP)

1. **Header**
   - Title: "Industry Update Monitor"
   - Stats: total items, unread by flag, last updated

2. **Filter bar**
   - Toggle flags: show only 🔴, or 🔴+🟠, or all
   - Date range picker (this week, last 2 weeks, all)
   - Source dropdown (filter by source)

3. **Item list**
   - Card per item: flag emoji | title | teaser | source | date
   - Checkbox to mark read (live update)
   - Link to source opens in new tab
   - If AI summary exists: toggle to show/hide

4. **Search box** (top)
   - Type to filter title + teaser
   - Auto-debounce

5. **No auth** (for now; personal use only)

---

## Deployment & Cost

### Vercel (free tier)
- Next.js app auto-deploys from GitHub
- 100 GB bandwidth/month
- Enough for personal use

### Supabase (free tier)
- PostgreSQL 500 MB
- ~1M API calls/month
- Enough for personal + moderate traffic
- Real-time updates included

### Worker scheduling
- Option A: Run manually via crontab (free)
- Option B: GitHub Actions (free)
- Option C: Later: Supabase Edge Functions (add if needed)

**Total cost: $0 until you add email or high volume.**

---

## Build Order

1. **Set up Next.js project** – scaffold, Vercel config
2. **Supabase schema** – create tables, enable RLS (row-level security off for MVP)
3. **Supabase client** – `lib/supabase.ts`, queries
4. **API routes** – GET /items, POST /items, POST /search
5. **Dashboard components** – ItemCard, FilterBar, SearchBox
6. **Dashboard page** – wire up API calls, real-time updates
7. **Python worker refactor** – add DB write logic
8. **Deploy & test** – Vercel + local worker end-to-end
9. **Later: email, AI, auth** – add as needed

---

## Notes for Phase 1B (later)

- AI summaries: store in `ai_summary` column, add `ai_generated_at` timestamp
- SendGrid integration: email weekly digest of 🔴+🟠 unread items (new route `/api/email/send`)
- Google Analytics: add to dashboard for usage tracking
- Dark mode: easy toggle with Tailwind (already built-in)

---

## Risk & Guardrails

**Supabase free tier limits:**
- 500 MB storage: ~10,000 items at 50 KB each. Plenty for 6 months of weekly feeds.
- If you hit limits: bump to paid ($25/mo) or archive old items.

**API cost:**
- Each dashboard page load = ~3 API calls (items, sources, counts).
- ~100 loads/day = 300 calls/day = 9K/month. Well under 1M limit.

**Data governance:**
- Same guardrails apply: store teaser + link only, never full article.
- Supabase auto-backups; respects your data.
- No public API key; secure RLS rules (add auth later if shared).

---

## Success Criteria for MVP

> **Corrected 17 September 2026.** Every line below was ticked ✅ while none of the database work
> had been done. The ticks were aspirations copied from the plan, not a record of anything
> passing. What is actually true, checked against the code on that date:

| Criterion | Real status |
|---|---|
| Python worker writes items to Supabase | ❌ **No.** The worker writes `web/lib/digest.json`. Nothing in `src/` mentions Supabase. |
| Dashboard loads items from Supabase | ❌ **No.** It reads `@/lib/digest`, the JSON file. `web/lib/supabase.ts` exists but **is imported by nothing**. |
| Filter by flag works | ✅ Yes, against the JSON file. |
| Mark item as read persists | ⚠️ **Locally only.** `localStorage` in one browser, so it does not follow you to another machine and is lost when site data is cleared. Not the database persistence this line meant. |
| Search queries work | ✅ Yes, via `web/app/api/search/route.ts`, against the JSON file. |
| Deploy to Vercel and access via public URL | ✅ Yes. |
| Existing `USE_AI` switch still works | ❌ **There is no `USE_AI` switch.** It has never existed in the code, in any branch. |
| No new cost | ✅ Yes, and unchanged by any of the above. |

So the dashboard works, and works well, on a JSON file. What was never built is the database
underneath it.

`@supabase/supabase-js` is still in `web/package.json` and `web/lib/supabase.ts` is still on disk,
imported by nothing. That dead client is the whole of item 7 in
[IMPROVEMENTS.md](IMPROVEMENTS.md): decide one way — connect it, or delete it and correct this
plan. Keeping both is what made this document misleading in the first place.

**Next: not "start building". That decision, first.**
