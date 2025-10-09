#!/usr/bin/env python3
"""
Get ALL Instagram cookies from browser.
This is more reliable than just sessionid.
"""

import json
import os

print("\n" + "="*60)
print("Get Instagram Cookies from Browser")
print("="*60 + "\n")

print("📝 Instructions:")
print("1. Open Instagram in your browser: https://instagram.com")
print("2. Make sure you're logged in")
print("3. Press F12 to open Developer Tools")
print("4. Go to: Application > Cookies > instagram.com")
print("5. Copy the VALUE of these cookies:\n")

cookies = {}

print("Cookie 1: sessionid")
sessionid = input("   Paste sessionid: ").strip()
if sessionid:
    cookies['sessionid'] = sessionid

print("\nCookie 2: ds_user_id")
ds_user_id = input("   Paste ds_user_id: ").strip()
if ds_user_id:
    cookies['ds_user_id'] = ds_user_id

print("\nCookie 3: csrftoken")
csrftoken = input("   Paste csrftoken: ").strip()
if csrftoken:
    cookies['csrftoken'] = csrftoken

print("\nCookie 4: rur (optional)")
rur = input("   Paste rur (or press Enter to skip): ").strip()
if rur:
    cookies['rur'] = rur

if not cookies.get('sessionid'):
    print("\n❌ sessionid is required!")
    exit(1)

print("\n🔄 Creating session file...")

# Create session data
session_data = {
    "cookies": cookies,
    "uuids": {
        "phone_id": "12345678-1234-1234-1234-123456789012",
        "uuid": "12345678-1234-1234-1234-123456789012",
        "client_session_id": "12345678-1234-1234-1234-123456789012",
        "advertising_id": "12345678-1234-1234-1234-123456789012",
        "device_id": "android-1234567890123456"
    },
    "mid": cookies.get('mid', ''),
    "ig_u_rur": cookies.get('rur', ''),
    "ig_www_claim": cookies.get('ig_www_claim', ''),
    "authorization_data": {},
    "user_id": cookies.get('ds_user_id', ''),
    "device_settings": {},
    "user_agent": "Instagram 123.0.0.21.114 Android"
}

# Save to file
os.makedirs("worker", exist_ok=True)
with open("worker/instagram_session.json", "w") as f:
    json.dump(session_data, f, indent=2)

print("✅ Session file created: worker/instagram_session.json")

# Try to verify
print("\n🔍 Testing session...")

try:
    import sys
    sys.path.insert(0, 'worker')
    from instagrapi import Client
    
    cl = Client()
    cl.load_settings("worker/instagram_session.json")
    
    # Try to get user info
    user_id = cl.user_id
    print(f"✅ Session is valid! User ID: {user_id}")
    
    # Save updated session
    cl.dump_settings("worker/instagram_session.json")
    
    print("\n🎉 Success! Now run: python test_instagram_simple.py")
    
except Exception as e:
    print(f"⚠️  Could not verify session: {e}")
    print("\nThe session file was created anyway.")
    print("Try running: python test_instagram_simple.py")
    print("\nIf it still doesn't work, the cookies may have expired.")
    print("Make sure you're logged into Instagram in the browser!")
