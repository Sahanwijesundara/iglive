# System Layout with Admin Dashboard

```mermaid
flowchart LR
    subgraph Vercel["Vercel App (`vercel_app/`)"]
        Webhook["/api/webhook"] -->|queues jobs| JobsTable[(Postgres jobs)]
        AdminAPI["/api/admin/*"] -->|reads/writes| WorkerSettings[(worker_settings)]
        AdminUI["/admin dashboard"]
    end

    subgraph Workers["Asynchronous Workers"]
        MainWorker["main bot worker"] -->|polls| JobsTable
        TGMSWorker["tgms_worker"] -->|polls| JobsTable
        ImageEngine["ig_image_engine pipeline"] -->|polls| QueueItems[(Queue items)]
    end

    subgraph Storage["Supabase PostgreSQL"]
        JobsTable
        WorkerSettings
        ManagedGroups[(managed_groups)]
        Points[(telegram_users)]
        JoinRequests[(join_requests)]
        SentMessages[(sent_messages)]
        BotHealth[(bot_health)]
        QueueItems
    end

    AdminUI -->|fetch metrics| AdminAPI
    AdminUI -->|update toggles| AdminAPI

    AdminAPI -->|GET/POST| ManagedGroups
    AdminAPI -->|metrics| JobsTable & TGMSWorker & BotHealth & Points

    TGMSWorker -->|writes status| ManagedGroups
    TGMSWorker -->|processes join| JoinRequests
    TGMSWorker -->|logs broadcasts| SentMessages
    MainWorker -->|uses settings| WorkerSettings
    ImageEngine -->|stores results| QueueItems

    subgraph External["Telegram & Instagram"]
        Telegram["Telegram Bots"]
        Instagram["Instagram Sources"]
    end

    Webhook -->|incoming updates| Telegram
    TGMSWorker -->|sends messages| Telegram
    ImageEngine -->|collects media| Instagram
```

## Notes
- **Operations**: Dashboard pulls metrics via `/api/admin/dashboard/metrics` and updates toggles through `/api/admin/worker-settings` in `vercel_app/api/webhook.py`.
- **Workers**: Main worker and `tgms_worker` consume jobs from the shared `jobs` table; the image engine reads `queue_items` for scoring tasks.
- **Storage**: Supabase tables include `managed_groups`, `telegram_users`, `join_requests`, `sent_messages`, `bot_health`, and `worker_settings`.
- **External Integrations**: Telegram supplies updates to the webhook and receives bot responses; the image engine scrapes and processes Instagram media.
