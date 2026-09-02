-- Industry Update Monitor Supabase Schema
-- Run this SQL in your Supabase project dashboard

-- Create items table
CREATE TABLE IF NOT EXISTS items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Content
  title TEXT NOT NULL,
  teaser TEXT,
  link TEXT NOT NULL,
  source_name TEXT NOT NULL,
  
  -- Flags
  flag VARCHAR(10) NOT NULL DEFAULT 'NOTE' CHECK (flag IN ('ACT', 'KNOW', 'NOTE')),
  
  -- State
  is_read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  
  -- Optional AI
  ai_summary TEXT,
  ai_generated_at TIMESTAMPTZ,
  
  -- Dedup key
  feed_guid TEXT UNIQUE,
  
  -- Search index
  CONSTRAINT valid_title CHECK (char_length(title) > 0),
  CONSTRAINT valid_link CHECK (char_length(link) > 0)
);

-- Create index for common queries
CREATE INDEX idx_items_created_at ON items(created_at DESC);
CREATE INDEX idx_items_flag ON items(flag);
CREATE INDEX idx_items_source ON items(source_name);
CREATE INDEX idx_items_is_read ON items(is_read);
CREATE INDEX idx_items_feed_guid ON items(feed_guid);

-- Full-text search index (optional, for faster search)
CREATE INDEX idx_items_search ON items USING GIN (
  to_tsvector('english', title || ' ' || COALESCE(teaser, ''))
);

-- Create sources table (optional, for metadata)
CREATE TABLE IF NOT EXISTS sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  feed_url TEXT,
  category VARCHAR(50) CHECK (category IN ('regulator', 'trade_press', 'newsletter', 'bookmark')),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create index on sources
CREATE INDEX idx_sources_name ON sources(name);
CREATE INDEX idx_sources_active ON sources(is_active);

-- Enable Row Level Security (RLS)
-- Since this is personal use, we'll disable RLS for now
-- If you ever share this, enable RLS and add policies
ALTER TABLE items DISABLE ROW LEVEL SECURITY;
ALTER TABLE sources DISABLE ROW LEVEL SECURITY;

-- Optional: Create a view for unread items by flag
CREATE OR REPLACE VIEW unread_by_flag AS
SELECT 
  flag,
  COUNT(*) as count
FROM items
WHERE is_read = FALSE
GROUP BY flag;

-- Optional: Create a view for recent items
CREATE OR REPLACE VIEW recent_items AS
SELECT *
FROM items
ORDER BY created_at DESC
LIMIT 50;

-- Grant usage (for anon key access)
GRANT USAGE ON SCHEMA public TO anon;
GRANT SELECT, INSERT, UPDATE ON public.items TO anon;
GRANT SELECT ON public.sources TO anon;
GRANT SELECT ON public.unread_by_flag TO anon;
GRANT SELECT ON public.recent_items TO anon;

-- Optional: Create stored procedure for batch operations
CREATE OR REPLACE FUNCTION mark_items_as_read(item_ids UUID[])
RETURNS TABLE(updated_count INT) AS $$
BEGIN
  RETURN QUERY
  WITH updated AS (
    UPDATE items
    SET is_read = TRUE, updated_at = now()
    WHERE id = ANY(item_ids)
    RETURNING 1
  )
  SELECT COUNT(*)::INT FROM updated;
END;
$$ LANGUAGE plpgsql;
