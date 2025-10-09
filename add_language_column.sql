-- Migration: Add language support to telegram_users table
-- Run this on your database to add language preference tracking

ALTER TABLE telegram_users 
ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en' NOT NULL;

-- Add index for faster language-based queries
CREATE INDEX IF NOT EXISTS idx_telegram_users_language ON telegram_users(language);

-- Update existing users to English (already default)
UPDATE telegram_users SET language = 'en' WHERE language IS NULL;
