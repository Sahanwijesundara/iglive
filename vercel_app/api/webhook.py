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
    - Receives a webhook from Telegram.
    - Inserts the payload into a 'jobs' table for background processing.
    - Returns an immediate 200 OK to Telegram.
    """
    if not engine:
        logger.error("Database engine is not available. Cannot process webhook.")
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    # 1. Receive and validate the webhook data
    try:
        update_data = request.get_json()
        if not update_data or 'update_id' not in update_data:
            logger.warning("Received an invalid or empty webhook payload.")
            return jsonify({"status": "error", "message": "Invalid payload"}), 400
    except Exception as e:
        logger.error(f"Error decoding JSON payload: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Bad request"}), 400

    update_id = update_data.get('update_id')
    logger.info(f"Received webhook with update_id: {update_id}")

    # Send immediate typing indicator for better UX
    try:
        if 'message' in update_data:
            chat_id = update_data['message'].get('chat', {}).get('id')
            if chat_id:
                httpx.post(
                    f"https://api.telegram.org/bot{os.environ.get('BOT_TOKEN')}/sendChatAction",
                    json={"chat_id": chat_id, "action": "typing"},
                    timeout=2.0,
                )
    except Exception as e:
        logger.warning(f"Could not send typing indicator: {e}")

    # 2. (Optional but Recommended) Deduplication Check
    # In a full implementation, you would check a Redis cache or a `processed_webhooks` table
    # to see if this update_id has already been processed. For the MVP, we can start by
    # inserting directly and add deduplication later.

    # 3. Insert the job into the database
    try:
        logger.info("Attempting to connect to the database to insert job...")
        with engine.connect() as connection:
            logger.info("Database connection successful. Beginning transaction.")
            with connection.begin() as transaction:
                try:
                    job_type = 'process_telegram_update'
                    insert_query = text("""
                        INSERT INTO jobs (job_type, payload, status, created_at, updated_at)
                        VALUES (:job_type, :payload, 'pending', :created_at, :updated_at)
                    """)
                    connection.execute(insert_query, {
                        'job_type': job_type,
                        'payload': json.dumps(update_data),
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    })
                    transaction.commit()
                    logger.info("Job insertion transaction committed.")
                except Exception:
                    transaction.rollback()
                    logger.error("Transaction rolled back due to an error.")
                    raise
        
        logger.info(f"Successfully queued job for update_id: {update_id}")

    except Exception as e:
        logger.error(f"Database error while inserting job for update_id {update_id}: {e}", exc_info=True)
        # Even if the DB insert fails, we might still want to return 200 OK to Telegram
        # to prevent retries, while logging the error for manual intervention.
        # However, for initial debugging, returning a 500 might be more informative.
        return jsonify({"status": "error", "message": "Failed to queue job"}), 500

    # 4. Return an immediate 200 OK response
    # This is critical to meet Telegram's requirement for a fast response.
    return jsonify({"status": "ok", "message": "Webhook received and queued"}), 200

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