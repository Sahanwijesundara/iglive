#!/usr/bin/env python3
"""
LOCAL Instagram Live Checker
=============================

Run this on your local PC to check Instagram for live broadcasts.
Connects to Railway's PostgreSQL database to update live status.

This script ONLY handles Instagram checking. The Telegram bot runs on Railway.

Usage:
    python local_instagram_checker.py

Environment Variables Required:
    - DATABASE_URL: PostgreSQL connection string (from Railway)
    - IG_USERNAME: Instagram username
    - IG_PASSWORD: Instagram password
    - IG_CHECK_INTERVAL: Check interval (optional, default 150)
"""

import os
import sys
import asyncio
import logging
import random
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment
load_dotenv()

# Setup logging with UTF-8 encoding for Windows
import io
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')),
        logging.FileHandler('instagram_checker.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Import Instagram service
sys.path.insert(0, 'worker')
from instagram_service import InstagramService, ensure_instagram_login

# Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
BASE_CHECK_INTERVAL = int(os.environ.get('IG_CHECK_INTERVAL', '150'))
MIN_INTERVAL = 120
MAX_INTERVAL = 240

def get_random_interval():
    """Get random check interval for stealth"""
    return random.randint(MIN_INTERVAL, MAX_INTERVAL)

# Database setup
if not DATABASE_URL:
    logger.error("DATABASE_URL not found in environment variables!")
    logger.error("Get this from Railway: Dashboard → Database → Variables → DATABASE_URL")
    sys.exit(1)

try:
    engine = create_engine(DATABASE_URL)
    SessionFactory = sessionmaker(bind=engine)
    logger.info("✅ Database connected successfully")
except Exception as e:
    logger.error(f"❌ Database connection failed: {e}")
    sys.exit(1)


async def check_and_update_lives():
    """
    Main loop: Check Instagram for lives and update database.
    """
    logger.info("="*60)
    logger.info("LOCAL INSTAGRAM CHECKER - STARTED")
    logger.info("="*60)
    logger.info("This script checks Instagram and updates Railway database")
    logger.info("Press Ctrl+C to stop")
    logger.info("="*60)
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while True:
        try:
            # Get Instagram service (with session)
            ig_service = await ensure_instagram_login()
            
            # Check for lives
            logger.info("🔍 Checking story tray for live broadcasts...")
            live_users = await ig_service.get_live_users()
            
            # Reset error counter on success
            consecutive_errors = 0
            
            # Update database
            session = SessionFactory()
            try:
                # Mark all as offline first
                session.execute(text("""
                    UPDATE insta_links
                    SET is_live = FALSE,
                        last_updated = :now
                    WHERE is_live = TRUE
                """), {'now': datetime.now(timezone.utc)})
                
                # Mark live users
                for user in live_users:
                    username = user['username'].lstrip('@')
                    
                    # Check if exists
                    exists = session.execute(
                        text("SELECT id FROM insta_links WHERE username = :username"),
                        {'username': username}
                    ).fetchone()
                    
                    if exists:
                        # Update existing
                        session.execute(text("""
                            UPDATE insta_links
                            SET is_live = TRUE,
                                last_live_at = :now,
                                total_lives = COALESCE(total_lives, 0) + CASE WHEN is_live = FALSE THEN 1 ELSE 0 END,
                                last_updated = :now
                            WHERE username = :username
                        """), {
                            'username': username,
                            'now': datetime.now(timezone.utc)
                        })
                        logger.info(f"✅ @{username} is LIVE (Viewers: {user['viewer_count']})")
                    else:
                        # Insert new
                        session.execute(text("""
                            INSERT INTO insta_links (username, is_live, last_live_at, total_lives, last_updated, link)
                            VALUES (:username, TRUE, :now, 1, :now, :link)
                        """), {
                            'username': username,
                            'now': datetime.now(timezone.utc),
                            'link': f'https://instagram.com/{username}'
                        })
                        logger.info(f"✅ NEW USER @{username} is LIVE (Viewers: {user['viewer_count']})")
                
                session.commit()
                logger.info(f"📊 Live status updated: {len(live_users)} user(s) live")
                
            except Exception as e:
                logger.error(f"❌ Database update error: {e}")
                session.rollback()
            finally:
                session.close()
            
            # Wait before next check (random interval for stealth)
            next_check = get_random_interval()
            logger.info(f"⏰ Next check in {next_check}s ({next_check/60:.1f} min)")
            logger.info("-"*60)
            await asyncio.sleep(next_check)
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Stopping Instagram checker...")
            break
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"❌ Error in main loop ({consecutive_errors}/{max_consecutive_errors}): {e}")
            
            if consecutive_errors >= max_consecutive_errors:
                logger.error("⚠️ Too many consecutive errors. Instagram account may be temporarily blocked.")
                logger.error("💡 Solutions:")
                logger.error("   1. Use Instagram app normally for 10-15 minutes")
                logger.error("   2. Wait 2-3 hours before retrying")
                logger.error("   3. Use a different Instagram account")
                logger.error("Waiting 1 hour before retry...")
                await asyncio.sleep(3600)  # Wait 1 hour
                consecutive_errors = 0
            else:
                # Wait longer on error
                error_wait = get_random_interval() * 2
                logger.warning(f"⏰ Waiting {error_wait}s before retry...")
                await asyncio.sleep(error_wait)


def main():
    """Entry point"""
    try:
        asyncio.run(check_and_update_lives())
    except KeyboardInterrupt:
        logger.info("\n✅ Instagram checker stopped")
        sys.exit(0)


if __name__ == '__main__':
    main()
