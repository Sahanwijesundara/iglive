# 🎯 Hybrid Setup Guide

## Architecture Overview

```
LOCAL PC (Your Computer)          RAILWAY (Cloud)
━━━━━━━━━━━━━━━━━━━━━━          ━━━━━━━━━━━━━━━━━
                                  
local_instagram_checker.py        worker/main.py
    │                                 │
    │ Checks Instagram                │ Handles Telegram
    │ Every 2-4 minutes               │ Bot commands
    │                                 │
    └──────────┬────────────────────┬─┘
               │                    │
               ▼                    ▼
         PostgreSQL Database
         (Hosted on Railway)
```

---

## ✅ Step 1: Deploy Railway Worker (Without Instagram)

### Push Updated Code

```powershell
git add worker/ local_instagram_checker.py HYBRID_SETUP.md
git commit -m "Split: Instagram checker local, bot on Railway"
git push origin main
```

### Railway Environment Variables

Make sure these are set in Railway dashboard:

```
DATABASE_URL=<auto-provided>
BOT_TOKEN=<your-telegram-bot-token>
```

**Remove these (not needed on Railway anymore):**
- ~~IG_USERNAME~~
- ~~IG_PASSWORD~~
- ~~IG_CHECK_INTERVAL~~

---

## ✅ Step 2: Setup Local Instagram Checker

### Install Dependencies

```powershell
cd "c:\IG live 2\Release 1.0\ig live(host ready)"
pip install -r worker/requirements.txt
```

### Create Local .env File

Create `.env` in the root folder:

```env
# Get this from Railway → Database → Variables → DATABASE_URL
DATABASE_URL=postgresql://postgres:...@...railway.app:5432/railway

# Your Instagram credentials
IG_USERNAME=l_jackson3146
IG_PASSWORD=your_password_here

# Check interval (optional)
IG_CHECK_INTERVAL=150
```

### Test It

```powershell
python local_instagram_checker.py
```

You should see:
```
✅ Database connected successfully
✅ Instagram session loaded
🔍 Checking story tray for live broadcasts...
✅ @username is LIVE (Viewers: 123)
📊 Live status updated: 1 user(s) live
⏰ Next check in 187s (3.1 min)
```

---

## ✅ Step 3: Run Local Checker 24/7

### Option A: Windows Task Scheduler

1. Open **Task Scheduler**
2. **Create Basic Task**
3. **Name:** "Instagram Live Checker"
4. **Trigger:** At startup
5. **Action:** Start a program
   - **Program:** `python`
   - **Arguments:** `local_instagram_checker.py`
   - **Start in:** `c:\IG live 2\Release 1.0\ig live(host ready)`
6. **Settings:**
   - ☑ Run whether user is logged on or not
   - ☑ Run with highest privileges
   - ☑ If task fails, restart every 1 minute

### Option B: PowerShell Background Process

```powershell
# Start
Start-Process python -ArgumentList "local_instagram_checker.py" -WorkingDirectory "c:\IG live 2\Release 1.0\ig live(host ready)" -WindowStyle Hidden

# Check if running
Get-Process python

# Stop (if needed)
Stop-Process -Name python
```

### Option C: NSSM (Recommended - Runs as Windows Service)

```powershell
# Install NSSM
choco install nssm

# Create service
nssm install IGLiveChecker python "c:\IG live 2\Release 1.0\ig live(host ready)\local_instagram_checker.py"
nssm set IGLiveChecker AppDirectory "c:\IG live 2\Release 1.0\ig live(host ready)"

# Start service
nssm start IGLiveChecker

# Service will auto-start on boot
```

---

## 🔍 How It Works

### Data Flow

1. **Local script checks Instagram** → Finds @user is live
2. **Writes to Railway database** → `UPDATE insta_links SET is_live = TRUE`
3. **User sends `/check_lives` to Telegram bot**
4. **Railway worker reads database** → Shows live users
5. **User clicks button** → Gets Instagram link

### Benefits

✅ **Instagram works** - Home IP, no blocks  
✅ **Bot always online** - Railway handles Telegram  
✅ **Database synced** - Both use same PostgreSQL  
✅ **Reliable** - Survives local PC restarts  
✅ **Cost** - $0 (Railway free tier)

---

## 📊 Monitoring

### View Local Checker Logs

```powershell
# Real-time
Get-Content instagram_checker.log -Wait

# Last 50 lines
Get-Content instagram_checker.log -Tail 50
```

### View Railway Logs

Railway Dashboard → Your Service → Deployments → Logs

### Test End-to-End

1. Start local checker: `python local_instagram_checker.py`
2. Wait 2-3 minutes for first check
3. Open Telegram bot
4. Send `/check_lives`
5. Should see live users!

---

## 🛠️ Troubleshooting

### Local Checker Won't Start

```powershell
# Check Python version
python --version  # Need 3.8+

# Reinstall dependencies
pip install -r worker/requirements.txt --upgrade

# Check DATABASE_URL
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DATABASE_URL'))"
```

### Can't Connect to Database

- Copy `DATABASE_URL` exactly from Railway
- Should start with `postgresql://`
- Test: `psql $DATABASE_URL` (if you have psql installed)

### Instagram Session Issues

- Session file: `worker/instagram_session.json`
- Already created locally - should work immediately
- If expired: Delete file, restart script, login again

### Bot Not Showing Lives

- Check Railway logs for errors
- Verify database connection on both ends
- Run SQL query: `SELECT * FROM insta_links WHERE is_live = TRUE;`

---

## 🔄 Updates

### Update Local Checker

```powershell
git pull origin main
# Restart local checker
```

### Update Railway Worker

```powershell
git push origin main
# Railway auto-deploys
```

---

## 💡 Power Management

### Handle Power Cuts

**Option 1: UPS** ($50-100)
- APC Back-UPS 600VA
- Keeps PC running 15-30 minutes
- Auto-shutdown script

**Option 2: Raspberry Pi** ($50)
- Ultra-low power (5W)
- Runs 24/7 cheaply
- Same Python script works

**Option 3: Always-On PC Setting**
- BIOS: AC Power Recovery → ON
- Windows: Power Options → Never sleep
- Auto-login enabled

---

## ✅ You're Done!

**Local:** Instagram checker running  
**Railway:** Telegram bot running  
**Database:** Connected and synced  

Send `/check_lives` to your Telegram bot to test! 🚀
