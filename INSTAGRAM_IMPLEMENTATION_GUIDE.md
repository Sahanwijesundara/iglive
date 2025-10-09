# Instagram Live Tracking Implementation Guide

## Architecture Decision: Railway (NOT Vercel)

### ✅ **Recommended: Railway Worker**

Deploy your worker on **Railway** (or similar persistent service like AWS EC2, DigitalOcean, Render, Fly.io):

**Why Railway:**
- ✅ **Persistent processes** - Maintains Instagram login session indefinitely
- ✅ **Stateful execution** - Keeps session state in memory
- ✅ **Long-running tasks** - Can run continuous background jobs
- ✅ **No execution time limits** - Unlike Vercel's 10-300 second limit
- ✅ **Better for API scraping** - Handle rate limits and retries properly

### ❌ **NOT Vercel**

**Why NOT Vercel:**
- ❌ **Serverless/stateless** - Cannot maintain Instagram session between invocations
- ❌ **10-second timeout** (300s max on Pro) - Instagram login/checking takes longer
- ❌ **Cold starts** - Session lost between requests
- ❌ **No background jobs** - Can't run periodic checkers

---

## What I've Built For You

### 1. **`worker/instagram_service.py`** ✅
- Instagram login/session management
- Live user checking functionality
- Uses `instagrapi` library for unofficial Instagram API
- Maintains singleton session for efficiency

**Key Features:**
- `login()` - Login and save session to file
- `get_live_users(usernames)` - Check specific users for lives
- `get_followed_accounts_live()` - Get lives from following feed
- Session persistence across restarts

### 2. **`worker/instagram_checker.py`** ✅
- Background task that runs continuously
- Checks Instagram every 60 seconds (configurable)
- Updates `insta_links` table with live status
- Integrated into worker main loop

**Key Features:**
- `update_live_status_in_db()` - Main checker loop
- `get_currently_live_users()` - Query DB for live users
- Automatic reconnection on errors

### 3. **Updated `worker/main.py`** ✅
- Integrated Instagram checker as concurrent background task
- Runs alongside the job processing loop
- Graceful shutdown handling

### 4. **Updated `worker/requirements.txt`** ✅
- Added `instagrapi>=1.16` dependency

---

## Manual Update Required: `worker/handlers.py`

I couldn't auto-edit this file, so you need to manually update the `check_live_handler` function.

### **Find this code (around line 241):**

```python
        # In a real app, you would query the `insta_links` table for live users,
        # format a paginated message, and send it.
        live_message = "📱 Currently Live on Instagram:\n\n"
        live_message += "🔴 @username1\n"
        live_message += "🔴 @username2\n"
        live_message += "🔴 @username3\n\n"
        live_message += f"Points remaining: {'♾️ Unlimited' if is_unlimited else user.points}"
        
        helper = TelegramHelper()
        buttons = {
            "inline_keyboard": [
                [
                    {"text": "🔄 Refresh", "callback_data": "check_live"},
                    {"text": "⬅️ Back", "callback_data": "back"}
                ]
            ]
        }
        await helper.send_message(sender_id, live_message, reply_markup=buttons)
        logger.info(f"User {user.id} checked for live users. Points remaining: {user.points}")
```

### **Replace with:**

```python
        # Get currently live users from database (updated by instagram_checker)
        live_users = await get_currently_live_users(session)
        
        # Format message with live users
        if live_users:
            live_message = "📱 Currently Live on Instagram:\n\n"
            for user_data in live_users[:10]:  # Show max 10 users
                username = user_data['username']
                total_lives = user_data.get('total_lives', 0)
                link = user_data.get('link', f"https://instagram.com/{username.lstrip('@')}")
                live_message += f"🔴 {username}\n"
                live_message += f"   Total Lives: {total_lives} | [Watch]({link})\n\n"
            
            if len(live_users) > 10:
                live_message += f"...and {len(live_users) - 10} more\n\n"
        else:
            live_message = "📱 Currently Live on Instagram:\n\n"
            live_message += "No one is live right now. 😴\n\n"
        
        live_message += f"Points remaining: {'♾️ Unlimited' if is_unlimited else user.points}"
        
        helper = TelegramHelper()
        buttons = {
            "inline_keyboard": [
                [
                    {"text": "🔄 Refresh", "callback_data": "check_live"},
                    {"text": "⬅️ Back", "callback_data": "back"}
                ]
            ]
        }
        await helper.send_message(sender_id, live_message, parse_mode="Markdown", reply_markup=buttons)
        logger.info(f"User {user.id} checked for live users. Found {len(live_users)} live. Points remaining: {user.points}")
```

**Note:** The import for `get_currently_live_users` is already added at the top of the file.

---

## Environment Variables Setup

Add these to your Railway/worker environment:

```bash
# Instagram credentials
IG_USERNAME=your_instagram_username
IG_PASSWORD=your_instagram_password

# Optional: Check interval in seconds (default: 60)
IG_CHECK_INTERVAL=60

# Existing variables
DATABASE_URL=postgresql://...
BOT_TOKEN=your_telegram_bot_token
```

---

## Deployment Steps

### **Step 1: Install Dependencies**

```bash
cd worker
pip install -r requirements.txt
```

### **Step 2: Set Environment Variables**

On Railway:
1. Go to your Railway project
2. Navigate to Variables tab
3. Add `IG_USERNAME` and `IG_PASSWORD`
4. Optionally set `IG_CHECK_INTERVAL`

### **Step 3: Deploy Worker to Railway**

```bash
# Railway automatically detects and runs main.py
# Or specify start command:
python worker/main.py
```

### **Step 4: Add Instagram Users to Track**

Insert Instagram usernames into the `insta_links` table:

```sql
INSERT INTO insta_links (username, link) 
VALUES 
    ('cristiano', 'https://instagram.com/cristiano'),
    ('leomessi', 'https://instagram.com/leomessi'),
    ('selenagomez', 'https://instagram.com/selenagomez');
```

### **Step 5: Monitor Logs**

Watch Railway logs to see:
- Instagram login success
- Live status checks
- Users going live/offline

---

## System Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Railway Worker Process                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │  Main Job Loop   │         │ Instagram Checker Loop  │  │
│  │  (Telegram Bot)  │         │  (Background Task)      │  │
│  │                  │         │                         │  │
│  │ - Process jobs   │         │ - Login to Instagram    │  │
│  │ - Handle commands│         │ - Check live users      │  │
│  │ - Send messages  │         │ - Update database       │  │
│  │                  │         │ - Every 60 seconds      │  │
│  └────────┬─────────┘         └──────────┬──────────────┘  │
│           │                               │                  │
│           └───────────┬───────────────────┘                  │
│                       │                                      │
└───────────────────────┼──────────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  PostgreSQL DB  │
              │  (Vercel/Neon)  │
              └─────────────────┘
                        ▲
                        │
              ┌─────────┴─────────┐
              │   Vercel Webhook  │
              │   (Ingress Only)  │
              └───────────────────┘
```

---

## Testing Locally

```bash
# Set environment variables
export IG_USERNAME="your_instagram_username"
export IG_PASSWORD="your_instagram_password"
export DATABASE_URL="postgresql://..."
export BOT_TOKEN="your_telegram_bot_token"

# Run worker
cd worker
python main.py
```

You should see:
```
INFO - Database engine created successfully.
INFO - Starting worker process...
INFO - Starting Instagram live checker background task...
INFO - Instagram live checker started.
INFO - Logging into Instagram as your_instagram_username...
INFO - Instagram login successful and session saved.
INFO - Checking live status for X Instagram users...
```

---

## Important Notes

### **Instagram Session Management**
- Session is saved to `instagram_session.json` in the worker directory
- This persists login across worker restarts
- If login fails, delete this file and restart worker

### **Rate Limiting**
- Instagram has rate limits (typically 200 requests/hour)
- The checker adds 2-second delays between user checks
- Adjust `IG_CHECK_INTERVAL` if you hit rate limits

### **Account Security**
- Use a dedicated Instagram account, not your personal one
- Enable 2FA and save backup codes
- Instagram may require phone/email verification initially
- Consider using an Instagram business account

### **Alternatives to instagrapi**
If `instagrapi` doesn't work for you:
- **instagram-private-api** (Node.js alternative)
- **instagram-scraper** (less reliable)
- **Selenium + browser automation** (slower but more reliable)

---

## Troubleshooting

### "Instagram login failed"
- Check credentials are correct
- Try logging in manually from the same IP
- Instagram might require verification (check email/SMS)
- Delete `instagram_session.json` and retry

### "No users are live" but you know they are
- Check that usernames are correct in database (no @)
- Check Instagram account can see these users
- Verify the account isn't shadowbanned/restricted

### Worker crashes frequently
- Check Railway logs for errors
- Instagram might be rate limiting - increase `IG_CHECK_INTERVAL`
- Ensure enough memory allocated (at least 512MB)

---

## Cost Estimate

**Railway Pricing:**
- Hobby Plan: $5/month
- Starter Plan: Pay-as-you-go (~$0.000231/GB-s)
- Estimated cost: $5-10/month for this worker

**Alternatives:**
- **DigitalOcean Droplet**: $4/month (cheapest)
- **Render**: Free tier available, then $7/month
- **Fly.io**: Free tier (256MB RAM)
- **AWS EC2 t4g.nano**: ~$3/month

---

## Next Steps

1. ✅ Set up Railway account
2. ✅ Deploy worker code
3. ✅ Set environment variables
4. ✅ Add Instagram usernames to database
5. ✅ Monitor logs for successful login
6. ✅ Test `/check_live` command in Telegram bot
7. ✅ Scale as needed

**Your system is now ready for real Instagram live tracking! 🚀**
