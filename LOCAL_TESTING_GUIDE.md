# Local Testing Guide - Instagram Live Tracking

## ✅ Implementation Status: COMPLETE

All code is ready! Now let's test it locally before deploying.

---

## Quick Test (5 minutes)

### 1. Install Dependencies

```powershell
cd "c:\IG live 2\Release 1.0\ig live(host ready)\worker"
pip install -r requirements.txt
```

### 2. Create `.env` File

Create a file named `.env` in the root directory:

```env
# Instagram credentials
IG_USERNAME=your_instagram_username
IG_PASSWORD=your_instagram_password

# Database (optional for basic test)
DATABASE_URL=your_postgresql_url

# Telegram (optional for basic test)
BOT_TOKEN=your_bot_token
```

### 3. Run Simple Test

```powershell
cd "c:\IG live 2\Release 1.0\ig live(host ready)"
python test_instagram_simple.py
```

**Expected Output:**
```
📱 Instagram Username: your_username
🔑 Password: **********

🔄 Logging into Instagram...
✅ Login successful!

🔍 Checking if popular accounts are live...
   Checking @cristiano... ⚫ Offline
   Checking @leomessi... ⚫ Offline
   Checking @therock... ⚫ Offline

✅ Test complete! Instagram API is working.
```

---

## Full Test Suite (10 minutes)

### Run Comprehensive Tests

```powershell
python test_instagram_local.py
```

This tests:
- ✅ Instagram login
- ✅ Checking specific users for lives
- ✅ Checking following feed
- ✅ Database integration

---

## Visual Debugging - See What's Happening

### Option 1: Run with Verbose Logging

```powershell
# Set environment variable for detailed logs
$env:PYTHONUNBUFFERED=1

# Run the worker
cd worker
python main.py
```

You'll see real-time output like:
```
INFO - Database engine created successfully.
INFO - Starting worker process...
INFO - Starting Instagram live checker background task...
INFO - Logging into Instagram as your_username...
INFO - Instagram login successful and session saved.
INFO - Checking live status for 5 Instagram users...
INFO - ✅ @username went LIVE! (Viewers: 150)
INFO - Live status check complete. 1/5 users are live.
```

### Option 2: Test Instagram Service Directly

Create a test script `test_my_account.py`:

```python
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    from worker.instagram_service import InstagramService
    
    # Login
    service = InstagramService()
    await service.login()
    
    # Check your following feed
    print("Checking who's live in your following...")
    lives = await service.get_followed_accounts_live()
    
    print(f"\nFound {len(lives)} live users:")
    for user in lives:
        print(f"🔴 {user['username']} - {user['viewer_count']} viewers")

asyncio.run(test())
```

Run it:
```powershell
python test_my_account.py
```

---

## Debugging Instagram Issues

### Issue: "Login failed"

**Possible causes:**
1. Wrong credentials
2. Instagram requires verification
3. Account flagged for suspicious activity

**Solutions:**
```powershell
# 1. Delete session file and retry
Remove-Item worker\instagram_session.json -ErrorAction SilentlyContinue
python test_instagram_simple.py

# 2. Try logging in manually from same IP first
# Open Instagram in browser, login, then retry script

# 3. Use a different Instagram account (not your personal one)
```

### Issue: "Challenge required"

Instagram wants to verify it's you. Two options:

**Option A: Handle challenge in code**
```python
# The instagrapi library can handle some challenges automatically
# It will prompt you for verification code
```

**Option B: Pre-verify the account**
1. Login to Instagram from the same IP
2. Complete any verification
3. Then run the script

### Issue: "Rate limited"

Instagram limits requests. Solutions:

```python
# In instagram_checker.py, increase the delay:
IG_CHECK_INTERVAL=120  # Check every 2 minutes instead of 1
```

Or in the service:
```python
# Increase sleep time between user checks
await asyncio.sleep(5)  # Instead of 2 seconds
```

---

## Testing Without Instagram (Mock Data)

If you want to test the bot logic without Instagram:

### 1. Create Mock Data in Database

```sql
-- Add some test users
INSERT INTO insta_links (username, is_live, total_lives, link) VALUES
    ('test_user1', true, 5, 'https://instagram.com/test_user1'),
    ('test_user2', false, 10, 'https://instagram.com/test_user2'),
    ('test_user3', true, 3, 'https://instagram.com/test_user3');
```

### 2. Test the Handler Directly

```python
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from worker.handlers import check_live_handler

async def test():
    # Setup database
    engine = create_engine(os.environ['DATABASE_URL'])
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Mock payload
    payload = {
        'callback_query': {
            'from': {
                'id': 123456789,  # Your Telegram user ID
                'username': 'testuser'
            }
        }
    }
    
    # Test handler
    await check_live_handler(session, payload)
    session.close()

asyncio.run(test())
```

---

## Monitoring Live Tracking

### Watch Logs in Real-Time

```powershell
# Run worker with output
cd worker
python main.py

# You'll see:
# - Every 60 seconds: "Checking live status for X users..."
# - When someone goes live: "✅ @username went LIVE!"
# - When someone goes offline: "📴 X user(s) went offline"
```

### Check Database Status

```sql
-- See who's currently live
SELECT username, is_live, last_live_at, total_lives 
FROM insta_links 
WHERE is_live = true;

-- See all tracked users
SELECT username, is_live, total_lives, last_updated 
FROM insta_links 
ORDER BY last_updated DESC;
```

---

## Performance Testing

### Test How Many Users You Can Track

```python
# Add many users to database
import asyncio
from worker.instagram_service import InstagramService

async def test_scale():
    service = InstagramService()
    await service.login()
    
    # Test with 50 users
    usernames = [f'user{i}' for i in range(50)]
    
    import time
    start = time.time()
    lives = await service.get_live_users(usernames)
    elapsed = time.time() - start
    
    print(f"Checked {len(usernames)} users in {elapsed:.2f} seconds")
    print(f"Rate: {len(usernames)/elapsed:.2f} users/second")

asyncio.run(test_scale())
```

**Expected results:**
- 50 users: ~100-150 seconds (with 2s delay between each)
- Rate limit: ~200 requests/hour from Instagram

---

## Headless Browser? (Not Needed!)

**Good news:** `instagrapi` doesn't use a browser at all! It's a pure API client.

**No Selenium, no Puppeteer, no browser needed!**

This means:
- ✅ Faster
- ✅ Less resource usage
- ✅ No browser dependencies
- ✅ Works on headless servers

---

## Common Test Scenarios

### Scenario 1: Test Login Only

```powershell
python -c "import asyncio; from worker.instagram_service import InstagramService; asyncio.run(InstagramService().login())"
```

### Scenario 2: Check One Specific User

```python
import asyncio
from worker.instagram_service import InstagramService

async def check_user(username):
    service = InstagramService()
    await service.login()
    result = await service.check_user_live(username)
    
    if result:
        print(f"🔴 {username} is LIVE with {result['viewer_count']} viewers!")
    else:
        print(f"⚫ {username} is not live")

# Check if Cristiano Ronaldo is live
asyncio.run(check_user('cristiano'))
```

### Scenario 3: Continuous Monitoring (Like Production)

```python
import asyncio
from worker.instagram_checker import update_live_status_in_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

async def monitor():
    engine = create_engine(os.environ['DATABASE_URL'])
    SessionFactory = sessionmaker(bind=engine)
    
    # This will run forever, checking every 60 seconds
    await update_live_status_in_db(SessionFactory)

asyncio.run(monitor())
```

---

## Troubleshooting Checklist

- [ ] Dependencies installed: `pip install -r worker/requirements.txt`
- [ ] `.env` file created with IG_USERNAME and IG_PASSWORD
- [ ] Instagram account can login manually
- [ ] No 2FA enabled (or backup codes ready)
- [ ] Account not flagged/restricted
- [ ] Database accessible (if testing full system)
- [ ] Python 3.8+ installed

---

## Next Steps After Local Testing

1. ✅ Verify login works locally
2. ✅ Test checking a few users
3. ✅ Add usernames to database
4. ✅ Deploy to Railway
5. ✅ Set environment variables on Railway
6. ✅ Monitor Railway logs
7. ✅ Test Telegram bot commands

---

## Quick Reference Commands

```powershell
# Install dependencies
pip install -r worker/requirements.txt

# Simple test
python test_instagram_simple.py

# Full test suite
python test_instagram_local.py

# Run worker locally
cd worker
python main.py

# Check database
psql $DATABASE_URL -c "SELECT * FROM insta_links WHERE is_live = true;"
```

---

**You're all set! The code is complete and ready to test! 🚀**
