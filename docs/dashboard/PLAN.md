# Admin Dashboard Plan

## Goals
- **[Monitor bot health]** Display queue depth, job failures, and worker heartbeats.
- **[Manage TGMS operations]** Surface join-request backlog, managed group status, and broadcasting activity.
- **[Control worker behavior]** Allow toggling features such as auto-approval and broadcast throttling without redeploying.

## Data Sources
- **[jobs]** Queue metrics (pending, processing, failed) scoped by `bot_token`.
- **[managed_groups]** Lifecycle status, activity phase, and failure counters.
- **[join_requests]** Approval pipeline statistics and outstanding requests.
- **[bot_health]** Worker heartbeat timestamps and status fields.
- **[sent_messages]** Broadcast delivery audit trail.

## Core Views
- **[Operations Overview]**
  - KPIs: pending jobs per bot, recent failures, last heartbeat per worker.
  - Charts: time-series of jobs processed per hour, failure rate.
- **[TGMS Join Requests]**
  - Table of pending requests with filters (group, requested_at).
  - Actions: approve/deny (trigger TGMS worker job).
- **[Managed Groups]**
  - Grid showing `phase`, `is_active`, `member_count`, `consecutive_failures`.
  - Controls to toggle broadcasting or deactivate a group.
- **[Broadcast Queue]**
  - Upcoming scheduled broadcasts and historical sends with `sent_messages` debug codes.
- **[Worker Settings]**
  - Toggle switches and numeric inputs for per-bot configuration flags.
  - Audit log of setting changes.

## Configuration Model
- **[worker_settings table]**
  - Columns: `setting_key`, `setting_value`, `bot_scope` (`main`/`tgms`/`global`), `updated_by`, `updated_at`.
  - Example keys: `auto_approve_join_requests`, `broadcast_cooldown_minutes`, `max_retry_count`.
- **[Access control]**
  - Reuse existing `ADMIN_API_KEY` for protected endpoints.
  - Optional: extend to multi-user auth later.

## API Endpoints
- **[GET /api/admin/dashboard/metrics]** Aggregate metrics for overview cards.
- **[GET /api/admin/worker-settings]** Fetch current configuration.
- **[POST /api/admin/worker-settings]** Update settings with validation and change log.
- **[POST /api/admin/tgms/approve]** Approve join requests (invokes TGMS handler).
- **[POST /api/admin/tgms/broadcast]** Schedule/queue broadcasts.

## UI Implementation Notes
- **[Framework]** Extend existing Vercel app (likely Next.js/React) with a protected `/admin` route.
- **[State management]** Client-side polling (5–10s) for metrics; optimistic updates for setting toggles.
- **[Feedback]** Toast notifications for API actions; highlight stale data if last refresh > 1 min.

## Rollout Steps
- **[Phase 1]** Implement `worker_settings` table, API endpoints, and wire workers to read settings on startup (and periodically refresh).
- **[Phase 2]** Build dashboard UI with overview + worker settings panels; add metrics endpoints.
- **[Phase 3]** Expand with TGMS join-request management, broadcast scheduling UI, alerting hooks.
- **[Phase 4]** Add role-based access, audit trails, and automated notifications (Telegram/email).

## Open Questions
- **[Auth strategy]** Stick with single API key or introduce Supabase Auth / OAuth?
- **[Settings refresh cadence]** Should workers poll settings periodically or react to webhooks?
- **[Alert thresholds]** Define SLA for queue size/latency before triggering alerts.
