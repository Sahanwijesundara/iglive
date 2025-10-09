# Quick Start: Instagram Live Tracking

## TL;DR - Where to Login

**✅ Use Railway (or similar persistent worker service)**
**❌ NOT Vercel (serverless limitations)**

---

## Why Railway?

| Feature | Railway ✅ | Vercel ❌ |
|---------|-----------|----------|
| Persistent Sessions | Yes | No (stateless) |
| Long-running processes | Yes | No (10-300s limit) |
| Background jobs | Yes | No |
| Instagram login | Works perfectly | Won't work |
| Cost | ~$5-10/month | Free but unsuitable |

---

## 3-Step Setup

### 1. Deploy Worker to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### 2. Set Environment Variables

In Railway dashboard, add:
```
IG_USERNAME=your_instagram_username
IG_PASSWORD=your_instagram_password
DATABASE_URL=postgresql://... (from Vercel Postgres)
BOT_TOKEN=your_telegram_bot_token
```

### 3. Manual Edit Required

Open `worker/handlers.py`, find line ~241, and replace the placeholder live users code with the real implementation from `INSTAGRAM_IMPLEMENTATION_GUIDE.md`.

---

## What Was Built

1. **`instagram_service.py`** - Instagram login & live checking
2. **`instagram_checker.py`** - Background task (runs every 60s)
3. **Updated `main.py`** - Integrated checker with worker
4. **Updated `requirements.txt`** - Added `instagrapi` library

---

## Architecture

```
Vercel (Webhook) → PostgreSQL ← Railway Worker (IG Login)
                                      ↓
                                  Instagram API
```

**Vercel**: Only receives webhooks, inserts jobs
**Railway**: Processes jobs, maintains IG session, checks lives

---

## Test It

```bash
# Run locally
cd worker
pip install -r requirements.txt
export IG_USERNAME="..."
export IG_PASSWORD="..."
python main.py
```

You should see:
```
✅ Instagram login successful
✅ Checking live status for X users
```

---

## Full Documentation

See `INSTAGRAM_IMPLEMENTATION_GUIDE.md` for complete details.

---

## Cost

- **Railway**: $5-10/month
- **Alternatives**: DigitalOcean ($4), Render (free tier), Fly.io (free tier)

**The official Instagram API doesn't support lives - unofficial libraries are the only way! 🎯**
