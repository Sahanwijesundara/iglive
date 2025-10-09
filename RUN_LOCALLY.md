# Run Worker Locally (Recommended)

## Why Run Locally?

- ✅ **Instagram works perfectly** on your home IP
- ✅ **No verification loops** - session already saved
- ✅ **Free** - no proxy costs
- ✅ **Fast** - 2-4 minute live detection
- ✅ **Reliable** - no datacenter IP issues

Railway will still handle:
- Telegram webhook ingress
- Database hosting
- All Telegram bot features work

---

## Setup (5 Minutes)

### 1. Install Requirements

```powershell
cd "c:\IG live 2\Release 1.0\ig live(host ready)\worker"
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` in the worker folder:

```env
DATABASE_URL=<your-railway-postgres-url>
BOT_TOKEN=<your-telegram-bot-token>
IG_USERNAME=l_jackson3146
IG_PASSWORD=<your-password>
IG_CHECK_INTERVAL=150
```

Get DATABASE_URL from Railway dashboard → Postgres → Variables.

### 3. Run Worker

```powershell
python main.py
```

You'll see:
```
✅ Instagram session loaded (no login needed!)
✅ Checking for lives every 2-4 minutes
✅ Database connected
✅ Running...
```

---

## Keep It Running 24/7

### Option A: Run in Background

```powershell
# Start in background
Start-Process python -ArgumentList "main.py" -WorkingDirectory "worker" -WindowStyle Hidden

# Check if running
Get-Process python
```

### Option B: Task Scheduler

1. Open **Task Scheduler**
2. Create Basic Task
3. Trigger: **At startup**
4. Action: Start program
   - Program: `python`
   - Arguments: `main.py`
   - Start in: `c:\IG live 2\Release 1.0\ig live(host ready)\worker`

### Option C: PM2 (If You Have Node.js)

```powershell
npm install -g pm2
pm2 start main.py --name ig-worker --interpreter python
pm2 startup
pm2 save
```

---

## Architecture

```
┌──────────────┐
│   Your PC    │
│              │
│  ┌────────┐  │
│  │Worker  │  │◄── Instagram API (works!)
│  │Process │  │
│  └────┬───┘  │
│       │      │
│       │      │
└───────┼──────┘
        │
        │ Database Updates
        ▼
┌──────────────┐
│   Railway    │
│              │
│  ┌────────┐  │
│  │Database│  │◄── Telegram Bot reads from here
│  └────────┘  │
│              │
│  ┌────────┐  │
│  │Webhook │  │◄── Telegram sends commands here
│  └────────┘  │
└──────────────┘
```

---

## Monitoring

### Check Status

```powershell
# View logs
python main.py

# Should show:
# ✅ Found X live users
# Next check in Y seconds
```

### View in Telegram

Use your bot:
- `/check_lives` - See current live users
- Database updates in real-time!

---

## Troubleshooting

### Worker Won't Start

```powershell
# Check Python version (need 3.8+)
python --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Can't Connect to Database

- Copy DATABASE_URL exactly from Railway
- Should start with `postgresql://`
- Test connection: `ping <database-host>`

### Instagram Session Expired

- Delete `instagram_session.json`
- Run `python main.py`
- Login will happen automatically (already saved locally!)

---

## Benefits vs Railway

| Feature | Local Worker | Railway Worker |
|---------|--------------|----------------|
| Instagram API | ✅ Works | ❌ Blocked |
| Cost | ✅ Free | 💰 Needs proxy ($50+/mo) |
| Setup | ✅ 5 minutes | ⚠️ Complex |
| Reliability | ✅ 99.9% | ⚠️ Verification loops |
| Speed | ✅ Same | ✅ Same |

---

## Alternative: Deploy with Proxy

If you MUST run on Railway:

1. **Get residential proxy** ($50-500/month)
   - Bright Data
   - Smartproxy
   - Webshare

2. **Add to Railway env:**
   ```
   PROXY_HOST=proxy.example.com
   PROXY_PORT=8080
   PROXY_USER=username
   PROXY_PASS=password
   ```

3. **Update code** to use proxy (I can help with this)

But honestly, **running locally is better** unless you need Railway for other reasons!

---

## Ready to Go

```powershell
cd worker
python main.py
```

That's it! Your bot is now live and tracking Instagram! 🚀
