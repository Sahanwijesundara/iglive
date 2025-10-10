# TGMS (Telegram Group Management System) Setup Guide

## Overview

TGMS is a separate worker that handles Telegram group management tasks including:
- Auto-approving join requests
- Broadcasting messages to managed groups
- Tracking member counts
- Managing group lifecycle (growth/monitoring phases)

## Architecture

```
Telegram Webhook → Vercel (webhook.py) → PostgreSQL (jobs table) → Workers
                                                                    ├─ Main Worker (handles regular bot updates)
                                                                    └─ TGMS Worker (handles group management)
```

### Job Routing

- **Main Worker** (`worker/main.py`): Processes jobs where `job_type NOT LIKE 'tgms_%'`
- **TGMS Worker** (`tgms_worker/main.py`): Processes jobs where `job_type LIKE 'tgms_%'`

## Components

### 1. Webhook Handler (`vercel_app/api/webhook.py`)

Routes incoming Telegram updates to the appropriate worker:
- `chat_join_request` → Job type: `tgms_process_join_request`
- Other updates → Job type: `process_telegram_update`

### 2. TGMS Worker (`tgms_worker/`)

**Files:**
- `main.py` - Entry point and job processor
- `database.py` - PostgreSQL adapter
- `telegram_api.py` - Telegram Bot API wrapper
- `group_sender.py` - Broadcasting with rate limiting
- `join_request_handler.py` - Auto-approval logic

**Job Types Handled:**
- `tgms_process_join_request` → Auto-approve join requests
- `tgms_send_to_groups` → Broadcast to managed groups
- `tgms_update_member_counts` → Update member counts
- `tgms_kick_inactive_members` → Kick inactive members (not implemented)

## Database Schema

### Tables Used by TGMS

**managed_groups**
- Stores groups under TGMS management
- Fields: `group_id`, `admin_user_id`, `title`, `phase`, `is_active`, `final_message_allowed`, `member_count`, `consecutive_failures`

**join_requests**
- Logs all join request events
- Fields: `request_id`, `user_id`, `chat_id`, `username`, `status`

**sent_messages**
- Tracks broadcast messages with debug codes
- Fields: `message_id`, `chat_id`, `telegram_message_id`, `debug_code`, `sent_at`

**bot_health**
- Monitors worker health
- Fields: `bot_name`, `status`, `last_activity`, `updated_at`

## Environment Variables

Required in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Main bot token (for regular bot operations)
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1uT0

# TGMS bot token (separate bot for group management)
TGMS_BOT_TOKEN=789012:XYZ-GHI5678jklMno-abc12D3e4fT5

# Admin API key for protected endpoints
ADMIN_API_KEY=your_secure_random_key_here
```

## Deployment

### 1. Deploy Vercel Webhook

```bash
cd vercel_app
vercel deploy
```

Set environment variables in Vercel dashboard:
- `DATABASE_URL`
- `BOT_TOKEN`
- `ADMIN_API_KEY`

### 2. Deploy Main Worker

Deploy `worker/` directory to Railway/Render:
- Set `DATABASE_URL` and `BOT_TOKEN`
- Start command: `python worker/main.py`

### 3. Deploy TGMS Worker

Deploy `tgms_worker/` directory to Railway/Render:
- Set `DATABASE_URL` and `TGMS_BOT_TOKEN`
- Start command: `python tgms_worker/main.py`

## API Endpoints

### `/api/webhook` (POST)
Main webhook endpoint for Telegram updates.

### `/api/tgms/send` (POST)
Admin endpoint to broadcast to managed groups.

**Headers:**
- `x-api-key`: `<ADMIN_API_KEY>`

**Body:**
```json
{
  "text": "Message text (if no photo)",
  "photo_url": "https://example.com/photo.jpg",
  "caption": "Photo caption with *Markdown*"
}
```

**Response:**
```json
{
  "status": "ok",
  "message": "Broadcast enqueued"
}
```

## Features

### Auto-Approval of Join Requests

When a user requests to join a managed group:
1. Webhook receives `chat_join_request` update
2. Creates job with type `tgms_process_join_request`
3. TGMS worker processes the request
4. Checks if group is managed and active
5. Auto-approves the request via Telegram API
6. Logs the request in `join_requests` table

### Broadcasting with Rate Limiting

When broadcasting to groups:
- Rate limit: 5 messages per second
- 3-second delay between groups
- Failure tracking: Auto-deactivates groups after 3 consecutive failures
- Debug codes: Unique codes appended to each message for tracking

### Group Phase Management

**Growth Phase:**
- Actively growing members
- Auto-approval enabled
- Broadcasting allowed

**Monitoring Phase:**
- Stable membership
- Auto-approval enabled
- Broadcasting allowed

## Local Development

### Run TGMS Worker Locally

```bash
cd "c:\IG live 2\Release 1.0\ig live(host ready)"
python -m tgms_worker.main
```

### Test Broadcasting

```bash
curl -X POST http://localhost:8000/api/tgms/send \
  -H "x-api-key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test broadcast"}'
```

## Monitoring

### Health Checks

The `bot_health` table tracks worker status:
```sql
SELECT * FROM bot_health WHERE bot_name = 'tgms_worker';
```

### Job Queue Status

Check pending TGMS jobs:
```sql
SELECT job_id, job_type, status, retries, created_at 
FROM jobs 
WHERE job_type LIKE 'tgms_%' AND status = 'pending'
ORDER BY created_at;
```

### Group Status

Check active managed groups:
```sql
SELECT group_id, title, phase, member_count, consecutive_failures, is_active
FROM managed_groups
WHERE is_active = true;
```

### Recent Broadcasts

Check recent sent messages:
```sql
SELECT chat_id, telegram_message_id, debug_code, sent_at
FROM sent_messages
ORDER BY sent_at DESC
LIMIT 10;
```

## Troubleshooting

### TGMS Worker Not Processing Jobs

1. Check if worker is running: `ps aux | grep tgms_worker`
2. Check database connection: Verify `DATABASE_URL`
3. Check bot token: Verify `TGMS_BOT_TOKEN` is valid
4. Check logs: Look for errors in worker output

### Broadcasting Failures

1. Check group is active: `SELECT * FROM managed_groups WHERE group_id = <id>`
2. Check consecutive_failures count
3. Verify bot is admin in the group
4. Check bot token permissions

### Join Requests Not Auto-Approved

1. Verify group exists in `managed_groups` table
2. Check `is_active = true` for the group
3. Verify TGMS bot is admin in the group with "Add Members" permission
4. Check `join_requests` table for failure status

## Security

- Store `TGMS_BOT_TOKEN` securely (never commit to git)
- Use strong `ADMIN_API_KEY` for protected endpoints
- Restrict `/api/tgms/send` endpoint to trusted sources only
- Use environment variables for all sensitive data

## Future Enhancements

- [ ] Implement kick inactive members feature
- [ ] Add webhook for group metrics
- [ ] Dashboard for group management
- [ ] Scheduled broadcasts
- [ ] A/B testing for broadcasts
