-- COMPLETE FIX for last_updated column type issue
-- Run this in Supabase SQL Editor

-- Step 1: Drop the problematic function/trigger if it exists
DROP FUNCTION IF EXISTS auto_end_old_lives() CASCADE;

-- Step 2: Add a new column with the correct type
ALTER TABLE insta_links ADD COLUMN last_updated_new TIMESTAMPTZ;

-- Step 3: Copy and convert existing data
UPDATE insta_links 
SET last_updated_new = CASE 
    WHEN last_updated IS NOT NULL AND last_updated != '' 
    THEN last_updated::TIMESTAMPTZ 
    ELSE NOW()
END;

-- Step 4: Drop the old TEXT column
ALTER TABLE insta_links DROP COLUMN last_updated;

-- Step 5: Rename the new column to the original name
ALTER TABLE insta_links RENAME COLUMN last_updated_new TO last_updated;

-- Step 6: Set default value for new rows
ALTER TABLE insta_links ALTER COLUMN last_updated SET DEFAULT NOW();

-- Step 7: Recreate the auto_end_old_lives function with correct types
CREATE OR REPLACE FUNCTION auto_end_old_lives()
RETURNS void AS $$
BEGIN
  UPDATE insta_links
  SET is_live = FALSE,
      last_updated = NOW()
  WHERE is_live = TRUE 
    AND last_updated < NOW() - INTERVAL '5 minutes';
END;
$$ LANGUAGE plpgsql;

-- Optional: Create a trigger to automatically end old lives
-- Uncomment if you want automatic cleanup
-- CREATE OR REPLACE FUNCTION trigger_auto_end_old_lives()
-- RETURNS TRIGGER AS $$
-- BEGIN
--   PERFORM auto_end_old_lives();
--   RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;

-- CREATE TRIGGER auto_cleanup_old_lives
-- AFTER INSERT OR UPDATE ON insta_links
-- FOR EACH STATEMENT
-- EXECUTE PROCEDURE trigger_auto_end_old_lives();

-- Step 8: Verify the change
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'insta_links' AND column_name = 'last_updated';

-- Step 9: Check existing data
SELECT username, is_live, last_updated 
FROM insta_links 
ORDER BY last_updated DESC NULLS LAST 
LIMIT 5;
