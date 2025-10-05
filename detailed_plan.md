# Final Hybrid Architecture: Vercel Ingress with Specialized Workers

This document describes the final, high-level architecture for the system. It is not a phased development plan but a blueprint of the components and their interactions. this is a optimized vertion of app.py to host online 

---

## Architectural Overview

The system is a hybrid, microservices-based architecture composed of three main parts: a Vercel Ingress Layer, Shared Infrastructure, and a set of Specialized Worker Services.

### 1. The Vercel Ingress Layer

A lightweight application deployed on Vercel that serves as the single entry point for all external HTTP traffic.

*   **Responsibilities**:
    *   Hosts all public API endpoints (e.g., `/api/send_messages`, `/api/groups`).
    *   **CRITICAL: Immediate 200 OK Response Pattern** for webhook handling:
        *   Receives all webhooks from Telegram at a single endpoint (`/api/webhooks/telegram`)
        *   **IMMEDIATE 200 OK**: Returns HTTP 200 response within 100ms of receiving webhook
        *   **Asynchronous Processing**: Queues validated webhook for background processing after responding
        *   **Timeout Prevention**: Avoids Telegram's 60-second webhook timeout through immediate acknowledgment
    *   Serves the web-based admin and monitoring dashboard.
    *   Performs initial request authentication (API keys) and validation.
    *   Acts as a "smart router," publishing validated job payloads to the appropriate message queues for backend processing.

### 2. Shared Infrastructure

These components form the backbone of the system, enabling communication and data persistence between the Vercel layer and the workers.

*   **Supabase (Primary Database)**: The central database and single source of truth for all system data (groups, users, bots, etc.). All services connect to this database with optimized connection pooling.
    *   **Connection Pooling Configuration**:
        *   **Pool Size**: 20-50 connections per worker service (configurable based on load)
        *   **Connection Timeout**: 30 seconds with automatic retry logic
        *   **Pool Management**: Automatic connection lifecycle management with health checks
        *   **Connection Reuse**: Intelligent connection reuse to minimize overhead
        *   **Failover Support**: Automatic failover to backup connections on failure
    *   **Supabase-Specific Features**:
        *   **Row Level Security (RLS)**: Database-level security policies for multi-tenant data access
        *   **Real-time Subscriptions**: WebSocket connections for live data updates
        *   **Built-in Auth**: Authentication management for admin and user access
        *   **Edge Functions**: Serverless functions for lightweight processing tasks
        *   **Database Backups**: Automated daily backups with point-in-time recovery
    *   **Connection Strategy**:
        *   **Vercel Layer**: Uses Supabase client with connection pooling for API endpoints
        *   **Worker Services**: Direct PostgreSQL connections with pgBouncer for optimal performance
        *   **Monitoring**: Connection pool metrics and alerting via Supabase dashboard
*   **Message Queue (e.g., AWS SQS, RabbitMQ)**: The asynchronous communication bus with Dead Letter Queue (DLQ) support and priority queue configuration for reliability:
    *   **Main Queues**:
        *   `group_message_queue`: For high-volume, bulk message sending jobs.
        *   `tgms_queue`: For group management and state-related tasks.
        *   `dm_queue`: For handling direct messages and user commands.
    *   **Priority Queue Configuration** ⚠️ **MAYBE - Consider for High Scale**:
        *   **Problem Solved**: Bulk operations (10k messages) blocking urgent tasks (join requests)
        *   **Priority Levels**:
            *   `high_priority`: Join requests, user commands, critical group management
            *   `normal_priority`: Regular message sending, scheduled tasks
            *   `low_priority`: Bulk operations, analytics, maintenance tasks
        *   **Processing Strategy**:
            *   **High Priority**: Processed immediately, smaller batch sizes (1-5 jobs)
            *   **Normal Priority**: Standard processing, medium batch sizes (5-20 jobs)
            *   **Low Priority**: Processed during off-peak hours, large batch sizes (50-100 jobs)
        *   **Queue Separation**: Separate physical queues for each priority level
        *   **Worker Allocation**: Dedicated workers for high-priority queues
    *   **Dead Letter Queues (DLQ)**:
        *   `group_message_queue_dlq`: Failed message sending jobs after 3 retries
        *   `tgms_queue_dlq`: Failed group management jobs after 3 retries
        *   `dm_queue_dlq`: Failed DM processing jobs after 3 retries
    *   **DLQ Configuration**:
        *   **Redrive Policy**: Max receive count of 3 before sending to DLQ
        *   **Monitoring**: CloudWatch alarms for DLQ depth > 10 messages
        *   **Admin Interface**: Endpoints to inspect and replay failed jobs
        *   **Alerting**: Notifications when DLQ messages need manual intervention
*   **Redis Cache (Upstash - Serverless)**: High-speed caching layer for webhook deduplication and session management:
    *   **Primary Use Case**: Webhook deduplication to prevent duplicate processing
    *   **Deduplication Logic**:
        *   Webhook received → Check Redis cache for `webhook:{update_id}`
        *   If exists: Skip processing (duplicate)
        *   If not exists: Mark as processing (5min expiry) → Queue for processing
    *   **Additional Features**:
        *   **Session Storage**: Temporary user session data and conversation state
        *   **Rate Limiting**: Per-user API rate limiting counters
        *   **Feature Flags**: Dynamic configuration management
    *   **Configuration**:
        *   **Provider**: Upstash Redis (Serverless, $0/month free tier: 10k requests/day)
        *   **Fallback**: PostgreSQL-based deduplication if Redis unavailable
        *   **Cleanup**: Automatic expiry of cached entries (5min for webhooks, 24h for sessions)

### 3. Specialized Worker Services (Microservices)

These are independent, long-running applications deployed on dedicated worker instances (e.g., AWS EC2, Fargate) that perform the core business logic.

*   **TGMS Worker**:
    *   **Source Code Foundation**: `telegram/tele_group_management_system.py`
    *   **Core Components**:
      *   **`TelegramGroupGrowthSystem`**: The main class orchestrating all subsystems.
      *   **`GroupStateMachine`**: Manages group lifecycle phases (`growth`, `monitoring`) and transitions.
      *   **`ActionQueueManager`**: A persistent, DB-backed queue for actions like approving joins or sending messages.
      *   **`MonitoringSystem`**: Tracks bot health, API usage, and system performance with alerting.
      *   **`GroupKicker`**: Handles automated removal of inactive members based on configurable rules.
      *   **`TelegramConnectionManager`**: Manages polling for `chat_join_request` updates and API-based backfilling.
      *   **`AntiDetectionSystem`**: Implements strategies to avoid detection by Telegram.
    *   **Responsibilities**:
      *   Initializes and manages all subsystems (`DatabaseManager`, `BotManager`, `AnalyticsEngine`, etc.).
      *   Ensures DB schema integrity, including a `UNIQUE` constraint on the `join_requests` table.
      *   Continuously polls for new join requests and backfills any missed requests using `getChatJoinRequests`.
      *   Schedules and executes hourly member kicking via the `GroupKicker`.
      *   Periodically updates member counts for all active groups.
      *   Runs the main system loop, processing state transitions for each active group.
      *   Sends periodic messages to groups based on `periodic_message_config.json`.
    *   **Communication**: Consumes jobs from the `tgms_queue`, interacts with the central **Supabase** database for all state persistence, and can publish new jobs to the shared message queue.

*   **Group Message Sender Worker**:
    *   **Source Code Foundation**: `telegram_managed_group_sender.py`
    *   **Core Components**:
      *   **`TelegramManagedGroupSender`**: The main class for sending messages to TGMS-managed groups.
      *   **`TokenBucket`**: A thread-safe class for rate limiting, configured to a 5 msg/sec refill rate.
      *   **`_create_advanced_keyboard`**: Constructs an inline keyboard with a "JOIN LIVE" button and an optional "BAN" button.
      *   **`send_to_managed_groups`**: The primary method that retrieves active groups from the database and sends them a message.
      *   **`delete_message_with_detailed_error`**: A robust function for deleting messages that provides detailed error logging and returns specific reasons for failure (e.g., `already_deleted`, `wrong_bot`).
    *   **Responsibilities**:
      *   Sends photo or text messages to all active groups listed in the `managed_groups` table of the **Supabase** database.
      *   Implements per-chat spacing (3s for groups, 1s for private) and global rate limiting (5 msg/sec).
      *   Checks a `final_message_allowed` flag for each group before sending.
      *   Appends a unique debug code (`DBG:xxxxxx`) to every message for tracking purposes.
      *   Tracks consecutive send failures for each group and automatically deactivates a group in the database after 3 failures.
      *   Logs every sent message and its debug code to `tgms_sent_debug_map.json`.
      *   Logs sent and deleted messages to a CSV file via `csv_message_tracker`.
    *   **Communication**: Consumes jobs from the `group_message_queue`, queries the central **Supabase** database for the list of active groups, calls the Telegram Bot API, and updates the `managed_groups` table in Supabase with failure counts.

*   **DM Handler Worker**:
    *   **Source Code Foundation**: `telegram_bot.py`
    *   **Core Components**:
      *   **Telethon Client**: Uses a `TelegramClient` to handle all user interactions.
      *   **Command Handlers**: A series of functions registered to handle specific commands (`/start`, `/init`, `/activate`) and callback queries (`check_live`, `my_account`).
      *   **Rate Limiting**: A `check_rate_limit` function restricts users to 10 commands per 60 seconds.
      *   **State Management**: A `conversation_states` dictionary tracks users engaged in multi-step processes like bot cloning.
      *   **`MetricsCollector`, `HealthMonitor`, `AnalyticsTracker`**: Classes for monitoring the bot's performance and health.
    *   **Responsibilities**:
      *   Handles the `/start` command to register new users, award initial points, and process referrals.
      *   Manages a daily points system where users receive 10 points each day, and checking for live users costs 1 point.
      *   Provides a referral system where users get a unique link (`/start <user_id>`) and earn 10 points per new user.
      *   Implements an "unlimited points" system:
          *   A group admin can use the `/init` command in their group to register it.
          *   The bot must be an admin in that group.
          *   The user can then use `/activate` in the group to confirm their admin status and receive unlimited points.
      *   Manages user accounts, including points, subscription status (legacy), and owned bots.
      *   Provides a paginated view of currently live Instagram users.
    *   **Communication**: Consumes jobs from the `dm_queue`, interacts with the central **Supabase** database for all user and group data, and sends responses via the Telethon client.

---

## Data and Control Flow Example

**CRITICAL TIMING: Immediate 200 OK Response Pattern with Deduplication**

1.  **User sends DM to bot** → Telegram webhook sent to Vercel (0s)
2.  **Vercel receives webhook** → **IMMEDIATE 200 OK response sent to Telegram (<100ms)**
3.  **Deduplication check**:
    *   Check Redis cache for `webhook:{update_id}`
    *   If duplicate: Skip processing and return
    *   If new: Mark as processing (5min expiry) → Continue
4.  **Asynchronous processing begins**:
    *   Vercel validates webhook payload and determines it's a private message
    *   Vercel publishes `process_private_message` job to `dm_queue`
    *   **DM Handler Worker** picks up job from queue
    *   Worker processes command and sends reply via Telegram Bot API
5.  **User receives response** (typically 1-3 seconds total, well under 60s timeout)

**Error Handling with DLQ:**
- **Job fails** → Retry up to 3 times → Send to DLQ if still failing
- **Admin alerted** → Manual inspection via `/admin/dlq/{queue_name}` endpoint
- **Bug fixed** → Replay successful jobs via `/admin/dlq/{queue_name}/replay`

**Why This Pattern is Critical:**
- **Telegram Timeout**: Webhooks must be acknowledged within 60 seconds or Telegram retries
- **Duplicate Prevention**: Redis deduplication prevents duplicate webhook processing
- **Reliability**: DLQ ensures no jobs are lost forever, enables manual recovery
- **User Experience**: Fast response times despite complex backend processing
- **Scalability**: Background processing allows handling multiple concurrent webhooks
