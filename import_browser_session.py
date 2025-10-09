#!/usr/bin/env python3
"""
Import Instagram session from browser.
Use this if direct login keeps failing.
"""

import sys
import os
sys.path.insert(0, 'worker')

from instagrapi import Client

print("\n" + "="*60)
print("Import Instagram Session from Browser")
print("="*60 + "\n")

username = input("Instagram username: ").strip()
password = input("Instagram password: ").strip()

print("\n📝 Instructions:")
print("1. Open Instagram in your browser")
print("2. Login if not already logged in")
print("3. Press F12 to open Developer Tools")
print("4. Go to: Application > Cookies > instagram.com")
print("5. Find the 'sessionid' cookie")
print("6. Copy its VALUE (long string)\n")

sessionid = input("Paste sessionid here: ").strip()

if not sessionid:
    print("❌ No sessionid provided!")
    sys.exit(1)

print("\n🔄 Creating session file...")

try:
    # Create client
    cl = Client()
    cl.set_user_agent("Instagram 123.0.0.21.114 Android")
    
    # Set the session
    cl.set_cookie("sessionid", sessionid)
    
    # Try to verify it works
    print("🔍 Verifying session...")
    user_id = cl.user_id_from_username(username)
    
    # Save session
    cl.dump_settings("worker/instagram_session.json")
    
    print("✅ Session saved successfully!")
    print("\n📝 Next steps:")
    print("   1. Update .env with your credentials")
    print("   2. Run: python test_instagram_simple.py")
    print("   3. It should work without asking for verification!\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nMake sure:")
    print("- You copied the correct sessionid")
    print("- You're logged into Instagram in browser")
    print("- The sessionid is the full value (very long string)")
