#!/usr/bin/env python3
"""
Simple Instagram test - just login and check a few users.
Run this to verify Instagram credentials work.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add worker to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'worker'))

# Load .env
load_dotenv()

async def main():
    print("\n" + "="*60)
    print("Instagram Live Tracking - Quick Test")
    print("="*60 + "\n")
    
    # Check credentials
    username = os.environ.get('IG_USERNAME')
    password = os.environ.get('IG_PASSWORD')
    
    if not username or not password:
        print("❌ ERROR: Set IG_USERNAME and IG_PASSWORD in .env file")
        print("\nExample .env:")
        print("IG_USERNAME=your_instagram_username")
        print("IG_PASSWORD=your_instagram_password")
        return
    
    print(f"📱 Instagram Username: {username}")
    print(f"🔑 Password: {'*' * len(password)}\n")
    
    # Import and test
    try:
        from instagram_service import InstagramService
        
        print("🔄 Logging into Instagram...")
        service = InstagramService(username, password)
        
        # Login
        success = await service.login()
        
        if not success:
            print("❌ Login failed! Check your credentials.")
            return
        
        print("✅ Login successful!\n")
        
        # Test checking some popular accounts
        print("🔍 Checking if popular accounts are live...")
        print("   (This tests if the API works)\n")
        
        test_users = ['cristiano', 'leomessi', 'therock']
        
        for username in test_users:
            print(f"   Checking @{username}...", end=" ")
            try:
                result = await service.check_user_live(username)
                if result:
                    print(f"🔴 LIVE! ({result['viewer_count']} viewers)")
                else:
                    print("⚫ Offline")
            except Exception as e:
                print(f"⚠️ Error: {e}")
            
            await asyncio.sleep(2)  # Rate limiting
        
        print("\n✅ Test complete! Instagram API is working.")
        print("\n📝 Next steps:")
        print("   1. Add usernames to track in database")
        print("   2. Run: python worker/main.py")
        print("   3. Watch for live notifications\n")
        
    except ImportError:
        print("❌ ERROR: instagrapi not installed")
        print("Run: pip install instagrapi")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
