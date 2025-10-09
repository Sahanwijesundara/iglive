#!/usr/bin/env python3
"""
Local testing script for Instagram live tracking.
This allows you to test Instagram login and live checking with visual output.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'worker'))

# Load environment variables
load_dotenv()

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Print colored header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


async def test_instagram_login():
    """Test Instagram login"""
    print_header("Testing Instagram Login")
    
    try:
        from worker.instagram_service import InstagramService
        
        # Check credentials
        username = os.environ.get('IG_USERNAME')
        password = os.environ.get('IG_PASSWORD')
        
        if not username or not password:
            print_error("Instagram credentials not set!")
            print_info("Set IG_USERNAME and IG_PASSWORD environment variables")
            return None
        
        print_info(f"Attempting to login as: {username}")
        
        # Create service and login
        service = InstagramService(username, password)
        success = await service.login()
        
        if success:
            print_success(f"Successfully logged in as {username}")
            print_info("Session saved to instagram_session.json")
            return service
        else:
            print_error("Login failed!")
            return None
            
    except ImportError as e:
        print_error(f"Missing dependency: {e}")
        print_info("Run: pip install instagrapi")
        return None
    except Exception as e:
        print_error(f"Login error: {e}")
        logger.exception("Full error:")
        return None


async def test_check_specific_users(service):
    """Test checking specific users for lives"""
    print_header("Testing Live Check for Specific Users")
    
    # Popular accounts that often go live
    test_usernames = [
        'cristiano',
        'leomessi', 
        'selenagomez',
        'kyliejenner',
        'therock'
    ]
    
    print_info(f"Checking {len(test_usernames)} users for live broadcasts...")
    print_info("This may take a few seconds (rate limiting)...\n")
    
    try:
        live_users = await service.get_live_users(test_usernames)
        
        if live_users:
            print_success(f"Found {len(live_users)} live user(s)!\n")
            for user in live_users:
                print(f"{Colors.OKGREEN}🔴 LIVE: {user['username']}{Colors.ENDC}")
                print(f"   Viewers: {user['viewer_count']}")
                print(f"   Broadcast ID: {user['broadcast_id']}")
                if user.get('title'):
                    print(f"   Title: {user['title']}")
                print()
        else:
            print_warning("No users are currently live")
            print_info("This is normal - these accounts don't go live frequently")
            
        return live_users
        
    except Exception as e:
        print_error(f"Error checking users: {e}")
        logger.exception("Full error:")
        return []


async def test_check_following_feed(service):
    """Test checking following feed for lives"""
    print_header("Testing Following Feed Live Check")
    
    print_info("Checking accounts you follow for live broadcasts...")
    
    try:
        live_users = await service.get_followed_accounts_live()
        
        if live_users:
            print_success(f"Found {len(live_users)} live user(s) in your following!\n")
            for user in live_users:
                print(f"{Colors.OKGREEN}🔴 LIVE: {user['username']}{Colors.ENDC}")
                print(f"   Viewers: {user['viewer_count']}")
                print(f"   Broadcast ID: {user['broadcast_id']}")
                if user.get('title'):
                    print(f"   Title: {user['title']}")
                print()
        else:
            print_warning("No one you follow is currently live")
            
        return live_users
        
    except Exception as e:
        print_error(f"Error checking following feed: {e}")
        logger.exception("Full error:")
        return []


async def test_database_integration():
    """Test database integration"""
    print_header("Testing Database Integration")
    
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            print_error("DATABASE_URL not set!")
            return False
        
        print_info("Connecting to database...")
        engine = create_engine(DATABASE_URL)
        SessionFactory = sessionmaker(bind=engine)
        session = SessionFactory()
        
        # Check if insta_links table exists
        result = session.execute(text("""
            SELECT COUNT(*) FROM insta_links
        """))
        count = result.scalar()
        
        print_success(f"Database connected! Found {count} Instagram links")
        
        # Show sample data
        if count > 0:
            result = session.execute(text("""
                SELECT username, is_live, total_lives 
                FROM insta_links 
                WHERE username IS NOT NULL 
                LIMIT 5
            """))
            
            print_info("\nSample tracked users:")
            for row in result:
                status = "🔴 LIVE" if row[1] else "⚫ Offline"
                print(f"  {status} @{row[0]} (Total lives: {row[2] or 0})")
        else:
            print_warning("No Instagram users in database yet")
            print_info("Add users with:")
            print("  INSERT INTO insta_links (username, link) VALUES ('username', 'https://instagram.com/username');")
        
        session.close()
        return True
        
    except Exception as e:
        print_error(f"Database error: {e}")
        logger.exception("Full error:")
        return False


async def main():
    """Main test function"""
    print(f"\n{Colors.BOLD}Instagram Live Tracking - Local Test Suite{Colors.ENDC}")
    print(f"{Colors.BOLD}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}\n")
    
    # Test 1: Instagram Login
    service = await test_instagram_login()
    if not service:
        print_error("\nCannot proceed without Instagram login")
        return
    
    # Test 2: Check specific users
    await test_check_specific_users(service)
    
    # Test 3: Check following feed
    await test_check_following_feed(service)
    
    # Test 4: Database integration
    await test_database_integration()
    
    # Summary
    print_header("Test Summary")
    print_success("All tests completed!")
    print_info("If login worked, you're ready to deploy to Railway")
    print_info("\nNext steps:")
    print("  1. Add Instagram usernames to insta_links table")
    print("  2. Deploy worker to Railway")
    print("  3. Set IG_USERNAME and IG_PASSWORD on Railway")
    print("  4. Monitor logs for live tracking\n")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_warning("\n\nTest interrupted by user")
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        logger.exception("Full error:")
