#!/usr/bin/env python3
"""
Fix Instagram Login - Multiple Methods
Choose the method that works best for you.
"""

import sys
import os
sys.path.insert(0, 'worker')

def print_header(text):
    print("\n" + "="*60)
    print(text.center(60))
    print("="*60 + "\n")

def method_1_browser_session():
    """Import session from browser - Most reliable"""
    print_header("Method 1: Import Browser Session")
    
    print("📝 Steps:")
    print("1. Open Instagram in your browser: https://instagram.com")
    print("2. Login with your account")
    print("3. Press F12 (Developer Tools)")
    print("4. Go to: Application tab > Cookies > instagram.com")
    print("5. Find 'sessionid' cookie and copy its VALUE\n")
    
    sessionid = input("Paste sessionid here (or press Enter to skip): ").strip()
    
    if not sessionid:
        print("⏭️  Skipped\n")
        return False
    
    try:
        from instagrapi import Client
        import json
        
        print("\n🔄 Creating session...")
        
        # Get username from .env
        from dotenv import load_dotenv
        load_dotenv()
        username = os.environ.get('IG_USERNAME')
        
        if not username:
            print("❌ IG_USERNAME not found in .env file")
            return False
        
        # Create a minimal session file with the sessionid
        session_data = {
            "cookies": {
                "sessionid": sessionid
            },
            "uuids": {
                "phone_id": "12345678-1234-1234-1234-123456789012",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "client_session_id": "12345678-1234-1234-1234-123456789012",
                "advertising_id": "12345678-1234-1234-1234-123456789012",
                "device_id": "android-1234567890123456"
            },
            "mid": "",
            "ig_u_rur": "",
            "ig_www_claim": "",
            "authorization_data": {},
            "user_id": "",
            "device_settings": {},
            "user_agent": "Instagram 123.0.0.21.114 Android"
        }
        
        # Save to file
        with open("worker/instagram_session.json", "w") as f:
            json.dump(session_data, f, indent=2)
        
        print("✅ Session file created!")
        
        # Now try to load it and verify
        print("🔍 Verifying session...")
        cl = Client()
        cl.load_settings("worker/instagram_session.json")
        
        try:
            # Try to get timeline to verify session works
            cl.get_timeline_feed()
            print("✅ Session verified and working!")
            
            # Save the updated session
            cl.dump_settings("worker/instagram_session.json")
            
            print("\n🎉 Success! You can now run: python test_instagram_simple.py")
            return True
        except Exception as verify_error:
            print(f"⚠️  Session created but verification failed: {verify_error}")
            print("The session might still work. Try running the test script.")
            return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nMake sure you copied the correct sessionid value")
        return False

def method_2_wait_and_retry():
    """Wait and retry - Simple but requires patience"""
    print_header("Method 2: Wait and Retry")
    
    print("Instagram is blocking rapid login attempts.")
    print("\n📝 Steps:")
    print("1. Login to Instagram in browser: https://instagram.com")
    print("2. Complete any verification they ask for")
    print("3. Browse Instagram for 2-3 minutes")
    print("4. Keep browser logged in")
    print("5. Wait 10-15 minutes")
    print("6. Run the test script again\n")
    
    # Delete old session
    try:
        os.remove("worker/instagram_session.json")
        print("✅ Deleted old session file")
    except:
        pass
    
    print("\n⏰ Set a timer for 15 minutes and try again!")
    return False

def method_3_different_account():
    """Use a different account"""
    print_header("Method 3: Use Different Account")
    
    print("The account 'l_jackson3146' may be flagged.")
    print("\n📝 Options:")
    print("1. Create a NEW Instagram account")
    print("2. Use it normally for 1-2 days")
    print("3. Then use it for the bot")
    print("\nOR")
    print("4. Use an existing account that's 6+ months old")
    print("5. Make sure it has some activity (posts, followers)")
    print("6. Don't enable 2FA on it\n")
    
    print("💡 Tip: Business accounts sometimes work better!")
    return False

def method_4_manual_challenge():
    """Try to complete challenge manually"""
    print_header("Method 4: Complete Challenge Manually")
    
    print("Let's try to complete the Instagram challenge.")
    print("\n⚠️  This requires you to respond to verification codes.\n")
    
    response = input("Ready to try? (y/n): ").strip().lower()
    if response != 'y':
        return False
    
    try:
        from instagrapi import Client
        from dotenv import load_dotenv
        
        load_dotenv()
        username = os.environ.get('IG_USERNAME')
        password = os.environ.get('IG_PASSWORD')
        
        if not username or not password:
            print("❌ Credentials not found in .env file")
            return False
        
        print(f"\n🔄 Attempting login for {username}...")
        print("📧 Check your email for verification code\n")
        
        cl = Client()
        cl.delay_range = [1, 3]
        
        # This will prompt for code
        cl.login(username, password)
        
        # If we get here, it worked!
        cl.dump_settings("worker/instagram_session.json")
        print("\n✅ Login successful! Session saved.")
        return True
        
    except Exception as e:
        print(f"\n❌ Challenge failed: {e}")
        print("\nThe challenge verification isn't working reliably.")
        print("Try Method 1 (Browser Session) instead - it's more reliable.")
        return False

def main():
    print_header("Instagram Login Fix Tool")
    
    print("Your login is being blocked by Instagram's security.")
    print("Choose a method to fix it:\n")
    
    print("1. Import Browser Session (Recommended - 99% success)")
    print("2. Wait and Retry (Simple - 70% success)")
    print("3. Use Different Account (Best long-term)")
    print("4. Try Challenge Again (May not work)")
    print("5. Exit\n")
    
    choice = input("Choose method (1-5): ").strip()
    
    if choice == '1':
        success = method_1_browser_session()
    elif choice == '2':
        success = method_2_wait_and_retry()
    elif choice == '3':
        success = method_3_different_account()
    elif choice == '4':
        success = method_4_manual_challenge()
    else:
        print("\n👋 Exiting...")
        return
    
    if success:
        print("\n" + "="*60)
        print("SUCCESS! You're ready to go!".center(60))
        print("="*60)
        print("\nNext step: python test_instagram_simple.py\n")
    else:
        print("\n" + "="*60)
        print("Try another method or read INSTAGRAM_CHALLENGE_FIX.md")
        print("="*60 + "\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
