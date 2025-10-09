#!/usr/bin/env python3
"""
Create Instagram session from the cookies you provided.
"""

import json
import os

print("\n" + "="*60)
print("Creating Instagram Session from Browser Cookies")
print("="*60 + "\n")

# Your cookies from the browser
cookies = {
    "sessionid": "44823616601%3AcxAFaoAt7oCBPE%3A17%3AAYiq3DNamc72bWzbMNG-QZrns-jErdAI3zoDFpgT2w",
    "ds_user_id": "44823616601",
    "csrftoken": "aKZIWMlbMAcdXiljjR7CmJ0O2bfVnYK1",
    "mid": "aLaeuwALAAFe4IWrSPEHgFC0qvsZ",
    "rur": '"CLN\\05444823616601\\0541791440577:01fedc493fa0f07eb8d1e33c1e3647fe2cfbc6309a54747cb40b6c636201e236362c3370"',
    "datr": "u562aPjwF0-_hun0BM45mHMV",
    "ig_did": "0BDF489B-BABC-482C-AFDB-266B3568F583",
    "ig_nrcb": "1"
}

# Create session data structure
session_data = {
    "cookies": cookies,
    "uuids": {
        "phone_id": "0BDF489B-BABC-482C-AFDB-266B3568F583",
        "uuid": "0BDF489B-BABC-482C-AFDB-266B3568F583",
        "client_session_id": "0BDF489B-BABC-482C-AFDB-266B3568F583",
        "advertising_id": "0BDF489B-BABC-482C-AFDB-266B3568F583",
        "device_id": "android-0bdf489bbabc482c"
    },
    "mid": "aLaeuwALAAFe4IWrSPEHgFC0qvsZ",
    "ig_u_rur": "CLN",
    "ig_www_claim": "0",
    "authorization_data": {
        "ds_user_id": "44823616601",
        "sessionid": "44823616601%3AcxAFaoAt7oCBPE%3A17%3AAYiq3DNamc72bWzbMNG-QZrns-jErdAI3zoDFpgT2w"
    },
    "user_id": "44823616601",
    "device_settings": {
        "app_version": "123.0.0.21.114",
        "android_version": 26,
        "android_release": "8.0.0",
        "dpi": "480dpi",
        "resolution": "1080x1920",
        "manufacturer": "OnePlus",
        "device": "devitron",
        "model": "6T Dev",
        "cpu": "qcom",
        "version_code": "185203708"
    },
    "user_agent": "Instagram 123.0.0.21.114 Android (26/8.0.0; 480dpi; 1080x1920; OnePlus; 6T Dev; devitron; qcom; en_US; 185203708)",
    "country": "US",
    "country_code": 1,
    "locale": "en_US",
    "timezone_offset": 19800
}

# Create worker directory if it doesn't exist
os.makedirs("worker", exist_ok=True)

# Save to file
session_file = "worker/instagram_session.json"
with open(session_file, "w") as f:
    json.dump(session_data, f, indent=2)

print(f"✅ Session file created: {session_file}")
print(f"📱 User ID: 44823616601")
print(f"🔑 Session ID: {cookies['sessionid'][:30]}...")

# Try to verify
print("\n🔍 Verifying session...")

try:
    import sys
    sys.path.insert(0, 'worker')
    from instagrapi import Client
    
    cl = Client()
    cl.load_settings(session_file)
    
    # Check if we have user_id
    if cl.user_id:
        print(f"✅ Session loaded! User ID: {cl.user_id}")
        
        # Try to get account info
        try:
            account_info = cl.account_info()
            print(f"✅ Account verified: @{account_info.username}")
            print(f"   Full name: {account_info.full_name}")
            print(f"   Followers: {account_info.follower_count}")
            
            # Save the verified session
            cl.dump_settings(session_file)
            print(f"\n✅ Session verified and saved!")
            
        except Exception as e:
            print(f"⚠️  Could not get account info: {e}")
            print("   But session file was created.")
    else:
        print("⚠️  Session loaded but user_id not found")
        print("   Session file was created anyway.")
    
    print("\n🎉 SUCCESS! Now run: python test_instagram_simple.py")
    print("   It should work without asking for verification!")
    
except Exception as e:
    print(f"⚠️  Could not verify: {e}")
    print("\nSession file was created anyway.")
    print("Try running: python test_instagram_simple.py")
    import traceback
    traceback.print_exc()
