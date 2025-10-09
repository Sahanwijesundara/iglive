-- Immediate cleanup of stale live statuses
-- Run this NOW in Supabase SQL Editor to clean up all those old records

-- Execute the cleanup function
SELECT expire_stale_live_statuses();

-- Verify the cleanup worked
SELECT 
  COUNT(*) FILTER (WHERE is_live = TRUE) as still_live,
  COUNT(*) FILTER (WHERE is_live = FALSE AND last_updated > NOW() - INTERVAL '1 hour') as recently_expired,
  COUNT(*) as total_rows
FROM insta_links;

-- Show any remaining live users (should be very few or none)
SELECT 
  username, 
  is_live, 
  last_updated,
  NOW() - last_updated AS age
FROM insta_links 
WHERE is_live = TRUE
ORDER BY last_updated DESC;
