# Final Hybrid Architecture: Vercel Ingress with Specialized Workers

This document describes the final, high-level architecture for the system. It is not a phased development plan but a blueprint of the components and their interactions.

---

## Architectural Overview

The system is a hybrid, microservices-based architecture composed of three main parts: a Vercel Ingress Layer, Shared Infrastructure, and a set of Specialized Worker Services.

### 1. The Vercel Ingress Layer

A lightweight application deployed on Vercel that serves as the single entry point for all external HTTP traffic.

*   **Responsibilities**:
    *   Hosts all public API endpoints (e.g., `/api/send_messages`, `/api/groups`).
    *   Receives all webhooks from Telegram at a single endpoint (`/api/webhooks/telegram`).
    *   Serves the web-based admin and monitoring dashboard.
    *   Performs initial request authentication (API keys) and validation.
    *   Acts as a "smart router," publishing validated job payloads to the appropriate message queues for backend processing.

### 2. Shared Infrastructure

These components form the backbone of the system, enabling communication and data persistence between the Vercel layer and the workers.

*   **Vercel Postgres**: The central database and single source of truth for all system data (groups, users, bots, etc.). All services connect to this database.
*   **Message Queue (e.g., AWS SQS, RabbitMQ)**: The asynchronous communication bus. It will have distinct queues for different types of work:
    *   `group_message_queue`: For high-volume, bulk message sending jobs.
    *   `tgms_queue`: For group management and state-related tasks.
    *   `dm_queue`: For handling direct messages and user commands.

### 3. Specialized Worker Services (Microservices)

These are independent, long-running applications deployed on dedicated worker instances (e.g., AWS EC2, Fargate) that perform the core business logic.

*   **TGMS Worker**:
    *   **Source Code Foundation**: `telegram/tele_group_management_system.py`
    *   **Responsibilities**: This is the stateful "brain" of group management. It runs a continuous loop to manage the entire lifecycle of all groups in the database (growth, monitoring phases), handles periodic tasks like kicking inactive members, and processes join requests.
    *   **Communication**: It consumes jobs from the `tgms_queue` (e.g., `process_join_request`) and interacts heavily with the Postgres database to read and update group states.

*   **Group Message Sender Worker**:
    *   **Source Code Foundation**: `telegram_managed_group_sender.py`
    *   **Responsibilities**: A stateless and highly scalable service dedicated exclusively to sending messages to groups. Its sole purpose is to process send jobs as quickly as possible.
    *   **Communication**: It consumes jobs from the `group_message_queue` (e.g., `send_final_message`), fetches the required user/group data from Postgres, and communicates with the Telegram API.

*   **DM Handler Worker**:
    *   **Source Code Foundation**: `telegram_bot.py`
    *   **Responsibilities**: Manages all 1-on-1 interactions with users. It processes commands sent via Direct Message, handles conversational logic, and responds to user queries.
    *   **Communication**: It consumes jobs from the `dm_queue` (e.g., `process_private_message`) and interacts with the database and Telegram API.

---

## Data and Control Flow Example

1.  A user sends a DM to the bot. Telegram sends a webhook to Vercel.
2.  The **Vercel Ingress Layer** receives the webhook, validates it, and sees it's a private message.
3.  Vercel publishes a `process_private_message` job to the `dm_queue`.
4.  The **DM Handler Worker** picks up the job, processes the command, and sends a reply back to the user via the Telegram API.
