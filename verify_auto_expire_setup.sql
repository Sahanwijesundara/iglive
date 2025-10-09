-- Verify that auto-expire is working correctly
-- Run this in Supabase SQL Editor

-- 1. Check that the cron job is scheduled
SELECT * FROM cron.job WHERE jobname = 'expire-stale-live-statuses';

-- 2. Manually trigger the cleanup to test it NOW
SELECT expire_stale_live_statuses();

-- 3. Check how many rows were affected
SELECT 
  COUNT(*) FILTER (WHERE is_live = TRUE) as currently_live,
  COUNT(*) FILTER (WHERE is_live = FALSE) as not_live,
  COUNT(*) as total
FROM insta_links;

-- 4. Show remaining live users (should be only recent ones)
SELECT 
  username, 
  is_live, 
  last_updated,
  NOW() - last_updated AS age,
  CASE 
    WHEN last_updated < NOW() - INTERVAL '5 minutes' THEN '⚠️ Should expire'
    ELSE '✅ Fresh'
  END AS status
FROM insta_links 
WHERE is_live = TRUE
ORDER BY last_updated DESC;

-- 5. Verify the trigger exists
SELECT 
  trigger_name, 
  event_manipulation, 
  event_object_table,
  action_statement
FROM information_schema.triggers 
WHERE trigger_name = 'trigger_update_last_updated';

-- 6. Check cron job run history (if available)
-- SELECT * FROM cron.job_run_details WHERE jobid = 1 ORDER BY start_time DESC LIMIT 5;
