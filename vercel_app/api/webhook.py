# vercel_app/api/webhook.py
import os
import json
import logging
from datetime import datetime

import httpx
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Database Connection ---
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()  # Strip whitespace
engine = None

# Log the database URL for debugging (masking the password)
if DATABASE_URL:
    try:
        safe_url = DATABASE_URL.split('@')[1]
        logger.info(f"DATABASE_URL found, connecting to: postgresql://postgres:****@{safe_url}")
    except Exception:
        logger.info("DATABASE_URL found, but could not parse for safe logging.")
else:
    logger.error("FATAL: DATABASE_URL environment variable not set.")

# Create engine separately to catch initialization errors
try:
    if DATABASE_URL:
        # Check if DATABASE_URL already contains sslmode parameter
        if 'sslmode=' in DATABASE_URL:
            # URL already has sslmode, don't add it in connect_args
            engine = create_engine(
                DATABASE_URL,
                poolclass=NullPool,
                pool_pre_ping=True
            )
            logger.info("Database engine created successfully (sslmode from URL).")
        else:
            # Add sslmode via connect_args only if not in URL
            engine = create_engine(
                DATABASE_URL,
                poolclass=NullPool,
                connect_args={"sslmode": "require"},
                pool_pre_ping=True
            )
            logger.info("Database engine created successfully (sslmode from connect_args).")
    else:
        logger.error("Skipping engine creation because DATABASE_URL is not set.")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}", exc_info=True)


@app.route('/api/webhook', methods=['POST'])
def handle_webhook():
    """
    Vercel Serverless Function to handle Telegram webhooks.
    Uses the X-Telegram-Bot-Token header to route updates to the
    correct handler for each bot.
    """
    if not engine:
        logger.error("Database engine is not available. Cannot process webhook.")
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    secret_header = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if not secret_header:
        logger.warning("Missing Telegram secret token header")
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    try:
        update_data = request.get_json()
        if not update_data or 'update_id' not in update_data:
            logger.warning("Received an invalid or empty webhook payload.")
            return jsonify({"status": "error", "message": "Invalid payload"}), 400
    except Exception as e:
        logger.error(f"Error decoding JSON payload: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Bad request"}), 400

    if secret_header == os.environ.get('TGMS_SECRET_TOKEN'):
        return _handle_tgms_update(update_data)

    if secret_header == os.environ.get('MAIN_SECRET_TOKEN'):
        return _handle_main_update(update_data)

    logger.warning("Rejected webhook from unauthorized secret token")
    return jsonify({"status": "error", "message": "Unauthorized"}), 403


def _handle_main_update(update_data: dict):
    """Handle updates for the main Telegram bot."""
    update_id = update_data.get('update_id')
    logger.info(f"Received main bot webhook with update_id: {update_id}")

    # Send immediate responses for better UX
    try:
        bot_token = os.environ.get('BOT_TOKEN')

        if 'callback_query' in update_data:
            callback_query_id = update_data['callback_query'].get('id')
            if callback_query_id:
                httpx.post(
                    f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
                    json={"callback_query_id": callback_query_id},
                    timeout=2.0,
                )

            chat_id = update_data['callback_query'].get('message', {}).get('chat', {}).get('id')
            if chat_id:
                httpx.post(
                    f"https://api.telegram.org/bot{bot_token}/sendChatAction",
                    json={"chat_id": chat_id, "action": "typing"},
                    timeout=2.0,
                )

        elif 'message' in update_data:
            chat_id = update_data['message'].get('chat', {}).get('id')
            if chat_id:
                httpx.post(
                    f"https://api.telegram.org/bot{bot_token}/sendChatAction",
                    json={"chat_id": chat_id, "action": "typing"},
                    timeout=2.0,
                )
    except Exception as e:
        logger.warning(f"Could not send immediate response: {e}")

    try:
        logger.info("Attempting to connect to the database to insert main bot job...")
        with engine.connect() as connection:
            logger.info("Main bot DB connection successful. Beginning transaction.")
            with connection.begin() as transaction:
                try:
                    if 'chat_join_request' in update_data:
                        job_type = 'tgms_process_join_request'
                        target_bot_token = os.environ.get('TGMS_BOT_TOKEN')
                    else:
                        job_type = 'process_telegram_update'
                        target_bot_token = os.environ.get('BOT_TOKEN')

                    insert_query = text("""
                        INSERT INTO jobs (job_type, bot_token, payload, status, created_at, updated_at)
                        VALUES (:job_type, :bot_token, :payload, 'pending', :created_at, :updated_at)
                    """)
                    connection.execute(insert_query, {
                        'job_type': job_type,
                        'bot_token': target_bot_token,
                        'payload': json.dumps(update_data),
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                    transaction.commit()
                    logger.info("Main bot job insertion committed.")
                except Exception:
                    transaction.rollback()
                    logger.error("Main bot transaction rolled back due to an error.")
                    raise

        logger.info(f"Successfully queued main bot job for update_id: {update_id}")
        return jsonify({"status": "ok", "message": "Webhook received and queued"}), 200

    except Exception as e:
        logger.error(f"Database error while inserting main bot job {update_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to queue job"}), 500


def _handle_tgms_update(update_data: dict):
    """Handle updates for the TGMS bot."""
    update_id = update_data.get('update_id')
    logger.info(f"Received TGMS webhook with update_id: {update_id}")

    try:
        with engine.connect() as connection:
            with connection.begin() as transaction:
                try:
                    if 'my_chat_member' in update_data:
                        new_status = update_data['my_chat_member'].get('new_chat_member', {}).get('status')
                        if new_status in {'administrator', 'creator'}:
                            job_type = 'tgms_register_group'
                        else:
                            job_type = 'tgms_process_update'
                    elif 'chat_join_request' in update_data:
                        job_type = 'tgms_process_join_request'
                    else:
                        job_type = 'tgms_process_update'

                    insert_query = text("""
                        INSERT INTO jobs (job_type, bot_token, payload, status, created_at, updated_at)
                        VALUES (:job_type, :bot_token, :payload, 'pending', :created_at, :updated_at)
                    """)
                    connection.execute(insert_query, {
                        'job_type': job_type,
                        'bot_token': os.environ.get('TGMS_BOT_TOKEN'),
                        'payload': json.dumps(update_data),
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                    transaction.commit()
                    logger.info("TGMS job insertion committed.")
                except Exception:
                    transaction.rollback()
                    logger.error("TGMS transaction rolled back due to an error.")
                    raise

        logger.info(f"Successfully queued TGMS job for update_id: {update_id}")
        return jsonify({"status": "ok", "message": "TGMS webhook received"}), 200

    except Exception as e:
        logger.error(f"Database error while inserting TGMS job {update_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to queue TGMS job"}), 500


@app.route('/api/admin/dashboard/metrics', methods=['GET'])
def get_dashboard_metrics():
    """Aggregate metrics for the admin dashboard."""
    if not engine:
        logger.error("Dashboard metrics requested but DB engine unavailable")
        return jsonify({"status": "error", "message": "Database unavailable"}), 500

    admin_key = os.environ.get('ADMIN_API_KEY')
    provided_key = request.headers.get('x-api-key')
    if not admin_key or provided_key != admin_key:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    metrics = {
        "members": {},
        "groups": [],
        "jobs": {"by_status": [], "by_bot": []},
        "tgms": {"register_group_jobs": []},
        "points": {},
        "queues": {},
        "errors": []
    }

    try:
        with engine.connect() as connection:
            # --- Member metrics ---
            try:
                total_users = connection.execute(text("SELECT COUNT(*) FROM telegram_users"))
                metrics["members"]["total"] = int(total_users.scalar() or 0)
            except Exception as exc:
                metrics["errors"].append(f"telegram_users.total: {exc}")

            try:
                active_7 = connection.execute(text(
                    """
                    SELECT COUNT(*) FROM telegram_users
                    WHERE COALESCE(last_seen, NOW()) >= NOW() - INTERVAL '7 days'
                    """
                ))
                active_30 = connection.execute(text(
                    """
                    SELECT COUNT(*) FROM telegram_users
                    WHERE COALESCE(last_seen, NOW()) >= NOW() - INTERVAL '30 days'
                    """
                ))
                metrics["members"]["active_7d"] = int(active_7.scalar() or 0)
                metrics["members"]["active_30d"] = int(active_30.scalar() or 0)
            except Exception as exc:
                metrics["errors"].append(f"telegram_users.active: {exc}")

            date_expr = "last_seen"
            try:
                created_exists = connection.execute(text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = current_schema()
                          AND table_name = 'telegram_users'
                          AND column_name = 'created_at'
                    )
                    """
                )).scalar()
                if created_exists:
                    date_expr = "COALESCE(created_at, last_seen)"
            except Exception:
                date_expr = "last_seen"

            try:
                new_last_7 = connection.execute(text(
                    f"""
                    SELECT COUNT(*) FROM telegram_users
                    WHERE {date_expr} >= NOW() - INTERVAL '7 days'
                    """
                ))
                metrics["members"]["new_last_7d"] = int(new_last_7.scalar() or 0)
            except Exception as exc:
                metrics["errors"].append(f"telegram_users.new_last_7d: {exc}")

            try:
                daily_rows = connection.execute(text(
                    f"""
                    SELECT TO_CHAR(date_bucket, 'YYYY-MM-DD') AS day, COUNT(*) AS count
                    FROM (
                        SELECT DATE_TRUNC('day', {date_expr}) AS date_bucket
                        FROM telegram_users
                        WHERE {date_expr} >= NOW() - INTERVAL '14 days'
                    ) AS daily
                    GROUP BY date_bucket
                    ORDER BY date_bucket
                    """
                )).fetchall()
                metrics["members"]["daily_joins_last_14d"] = [
                    {"day": row._mapping["day"], "count": int(row._mapping["count"])}
                    for row in daily_rows
                ]
            except Exception as exc:
                metrics["errors"].append(f"telegram_users.daily_joins: {exc}")

            # --- Managed groups ---
            try:
                group_rows = connection.execute(text(
                    """
                    SELECT group_id, title, member_count, phase, is_active,
                           consecutive_failures, updated_at
                    FROM managed_groups
                    ORDER BY member_count DESC
                    LIMIT 100
                    """
                )).fetchall()
                metrics["groups"] = [
                    {
                        "group_id": row._mapping["group_id"],
                        "title": row._mapping.get("title"),
                        "member_count": row._mapping.get("member_count"),
                        "phase": row._mapping.get("phase"),
                        "is_active": row._mapping.get("is_active"),
                        "consecutive_failures": row._mapping.get("consecutive_failures"),
                        "updated_at": row._mapping.get("updated_at"),
                    }
                    for row in group_rows
                ]
            except Exception as exc:
                metrics["errors"].append(f"managed_groups.list: {exc}")

            # --- Jobs ---
            try:
                status_rows = connection.execute(text(
                    "SELECT status, COUNT(*) AS count FROM jobs GROUP BY status"
                )).fetchall()
                metrics["jobs"]["by_status"] = [
                    {"status": row._mapping["status"], "count": int(row._mapping["count"])}
                    for row in status_rows
                ]
            except Exception as exc:
                metrics["errors"].append(f"jobs.by_status: {exc}")

            try:
                bot_rows = connection.execute(text(
                    """
                    SELECT COALESCE(bot_token, 'unknown') AS bot_token,
                           status,
                           COUNT(*) AS count
                    FROM jobs
                    GROUP BY COALESCE(bot_token, 'unknown'), status
                    """
                )).fetchall()
                metrics["jobs"]["by_bot"] = [
                    {
                        "bot_token": row._mapping["bot_token"],
                        "status": row._mapping["status"],
                        "count": int(row._mapping["count"]),
                    }
                    for row in bot_rows
                ]
            except Exception as exc:
                metrics["errors"].append(f"jobs.by_bot: {exc}")

            try:
                register_rows = connection.execute(text(
                    """
                    SELECT status, COUNT(*) AS count
                    FROM jobs
                    WHERE job_type = 'tgms_register_group'
                    GROUP BY status
                    """
                )).fetchall()
                metrics["tgms"]["register_group_jobs"] = [
                    {"status": row._mapping["status"], "count": int(row._mapping["count"])}
                    for row in register_rows
                ]
            except Exception as exc:
                metrics["errors"].append(f"jobs.register_group: {exc}")

            # --- Points ---
            try:
                points_row = connection.execute(text(
                    """
                    SELECT
                        AVG(daily_points) AS avg_daily,
                        AVG(lifetime_points) AS avg_lifetime,
                        SUM(CASE WHEN daily_points <= 0 THEN 1 ELSE 0 END) AS zero_daily
                    FROM telegram_users
                    """
                )).first()
                if points_row:
                    metrics["points"] = {
                        "avg_daily_points": float(points_row._mapping.get("avg_daily") or 0.0),
                        "avg_lifetime_points": float(points_row._mapping.get("avg_lifetime") or 0.0),
                        "users_zero_daily": int(points_row._mapping.get("zero_daily") or 0),
                    }
            except Exception as exc:
                metrics["errors"].append(f"telegram_users.points: {exc}")

            # --- Queue items (image engine) ---
            try:
                queue_row = connection.execute(text(
                    """
                    SELECT
                        SUM(CASE WHEN processed = false THEN 1 ELSE 0 END) AS pending,
                        COUNT(*) AS total
                    FROM queue_items
                    """
                )).first()
                if queue_row:
                    metrics["queues"]["image_engine"] = {
                        "pending": int(queue_row._mapping.get("pending") or 0),
                        "total": int(queue_row._mapping.get("total") or 0),
                    }
            except Exception as exc:
                metrics["errors"].append(f"queue_items.image_engine: {exc}")

            # --- Bot health ---
            try:
                health_rows = connection.execute(text(
                    "SELECT bot_name, status, updated_at, last_activity FROM bot_health"
                )).fetchall()
                metrics["bot_health"] = [
                    {
                        "bot_name": row._mapping["bot_name"],
                        "status": row._mapping.get("status"),
                        "updated_at": row._mapping.get("updated_at"),
                        "last_activity": row._mapping.get("last_activity"),
                    }
                    for row in health_rows
                ]
            except Exception as exc:
                metrics["errors"].append(f"bot_health.list: {exc}")

    except Exception as exc:
        logger.error(f"Failed to build dashboard metrics: {exc}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to build metrics"}), 500

    return jsonify({"status": "ok", "data": metrics}), 200


@app.route('/api/tgms/send', methods=['POST'])
def enqueue_tgms_send():
    """
    Admin endpoint to enqueue a broadcast to managed groups.
    Body JSON: { "text": "...", "photo_url": "...", "caption": "..." }
    Requires ADMIN_API_KEY environment variable and 'x-api-key' header.
    """
    if not engine:
        return jsonify({"status": "error", "message": "DB not ready"}), 500

    admin_key = os.environ.get('ADMIN_API_KEY')
    provided_key = request.headers.get('x-api-key')
    if not admin_key or provided_key != admin_key:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    payload = request.get_json(force=True) or {}
    job_type = 'tgms_send_to_groups'
    try:
        with engine.connect() as connection:
            with connection.begin() as transaction:
                try:
                    insert_query = text("""
                        INSERT INTO jobs (job_type, bot_token, payload, status, created_at, updated_at)
                        VALUES (:job_type, :bot_token, :payload, 'pending', :created_at, :updated_at)
                    """)
                    connection.execute(insert_query, {
                        'job_type': job_type,
                        'bot_token': os.environ.get('TGMS_BOT_TOKEN'),
                        'payload': json.dumps(payload),
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                    transaction.commit()
                except Exception:
                    transaction.rollback()
                    raise
        return jsonify({"status": "ok", "message": "Broadcast enqueued"}), 200
    except Exception as e:
        logger.error(f"Failed to enqueue tgms send: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to enqueue"}), 500

@app.route('/', methods=['GET'])
def index():
    """A simple health check endpoint for the root URL."""
    return "<h1>Vercel Webhook Ingress is running.</h1>", 200

# This part is not strictly necessary for Vercel, which uses its own serving mechanism,
# but it's useful for local testing.
if __name__ == '__main__':
    # To run this locally:
    # 1. Make sure you have Flask and SQLAlchemy installed (`pip install Flask SQLAlchemy psycopg2-binary`).
    # 2. Set the DATABASE_URL environment variable.
    # 3. Run `python vercel_app/api/webhook.py`.
    app.run(debug=True, port=8000)