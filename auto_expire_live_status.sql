-- Auto-expire stale live statuses after 5 minutes
-- Run this in Supabase SQL Editor

-- Step 1: Ensure last_updated has a default and auto-updates
-- (This should already be done from the previous migration)

-- Step 2: Create a function to expire old live statuses
CREATE OR REPLACE FUNCTION expire_stale_live_statuses()
RETURNS void AS $$
BEGIN
  UPDATE insta_links
  SET is_live = FALSE
  WHERE is_live = TRUE 
    AND last_updated < NOW() - INTERVAL '5 minutes';
    
  -- Optional: Log how many rows were updated
  -- RAISE NOTICE 'Expired % stale live statuses', ROW_COUNT();
END;
$$ LANGUAGE plpgsql;

-- Step 3: Set up automatic trigger on UPDATE/INSERT to update last_updated
CREATE OR REPLACE FUNCTION update_last_updated_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  -- Only update last_updated if is_live actually changed
  IF (TG_OP = 'INSERT') OR (OLD.is_live IS DISTINCT FROM NEW.is_live) THEN
    NEW.last_updated = NOW();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_last_updated ON insta_links;
CREATE TRIGGER trigger_update_last_updated
BEFORE INSERT OR UPDATE ON insta_links
FOR EACH ROW
EXECUTE FUNCTION update_last_updated_timestamp();

-- Step 4: Enable pg_cron extension (if not already enabled)
-- This allows scheduled jobs in PostgreSQL
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Step 5: Schedule the cleanup function to run every 2 minutes
-- This ensures live statuses expire within 7 minutes max (5 min + 2 min check interval)
SELECT cron.schedule(
  'expire-stale-live-statuses',  -- job name
  '*/2 * * * *',                 -- every 2 minutes (cron format)
  'SELECT expire_stale_live_statuses();'
);

-- Optional: View scheduled jobs
-- SELECT * FROM cron.job;

-- Optional: Unschedule the job (if you need to remove it later)
-- SELECT cron.unschedule('expire-stale-live-statuses');

-- Step 6: Test the function manually
-- SELECT expire_stale_live_statuses();

-- Step 7: Check current live statuses and their last_updated times
SELECT 
  username, 
  is_live, 
  last_updated,
  NOW() - last_updated AS age,
  CASE 
    WHEN last_updated < NOW() - INTERVAL '5 minutes' THEN 'Should expire'
    ELSE 'Still fresh'
  END AS status
FROM insta_links 
WHERE is_live = TRUE
ORDER BY last_updated DESC;
