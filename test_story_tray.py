#!/usr/bin/env python3
"""
Test the story tray live checking (the correct way!)
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.insert(0, 'worker')
load_dotenv()

async def main():
    print("\n" + "="*60)
    print("Testing Instagram Story Tray Live Checking")
    print("="*60 + "\n")
    
    from instagram_service import InstagramService
    
    print("🔄 Loading saved session...")
    service = InstagramService()
    
    # Login (will use saved session)
    success = await service.login()
    
    if not success:
        print("❌ Login failed!")
        return
    
    print("✅ Logged in successfully!\n")
    
    print("🔍 Checking story tray for live broadcasts...")
    print("   (This checks people YOU follow who are live)\n")
    
    live_users = await service.get_live_users()
    
    if live_users:
        print(f"✅ Found {len(live_users)} live user(s)!\n")
        for user in live_users:
            print(f"🔴 {user['username']}")
            print(f"   Viewers: {user['viewer_count']}")
            print(f"   Broadcast ID: {user['broadcast_id']}")
            if user.get('title'):
                print(f"   Title: {user['title']}")
            print()
    else:
        print("📴 No one you follow is currently live.\n")
        print("💡 Tip: Follow some active Instagram accounts to see lives!")
        print("   Popular accounts that often go live:")
        print("   - @cristiano")
        print("   - @leomessi")
        print("   - @therock")
        print("   - @kyliejenner\n")
    
    print("="*60)
    print("✅ Test complete!")
    print("="*60)
    print("\n📝 This is how the worker will check for lives:")
    print("   - Every 60 seconds")
    print("   - Checks story tray (people you follow)")
    print("   - Updates database automatically")
    print("   - No rate limits or API errors!\n")

if __name__ == '__main__':
    asyncio.run(main())
