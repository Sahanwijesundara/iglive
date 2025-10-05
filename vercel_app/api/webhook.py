# vercel_app/api/webhook.py

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Database Connection ---
# Vercel will provide the DATABASE_URL environment variable.
# Ensure it's configured in your Vercel project settings.
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    # A fallback for local development, if needed.
    # Replace with your actual Supabase connection string for local testing.
    logger.warning("DATABASE_URL environment variable not set. Using a default local fallback.")
    DATABASE_URL = "postgresql://user:password@host:port/database"

try:
    engine = create_engine(DATABASE_URL)
    logger.info("Database engine created successfully.")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}", exc_info=True)
    engine = None

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

    # 2. (Optional but Recommended) Deduplication Check
    # In a full implementation, you would check a Redis cache or a `processed_webhooks` table
    # to see if this update_id has already been processed. For the MVP, we can start by
    # inserting directly and add deduplication later.

    # 3. Insert the job into the database
    try:
        with engine.connect() as connection:
            # The job_type can be determined by inspecting the payload structure.
            # For this MVP, we'll use a generic 'process_telegram_update' type.
            job_type = 'process_telegram_update'
            
            insert_query = text("""
                INSERT INTO jobs (job_type, payload, status, created_at, updated_at)
                VALUES (:job_type, :payload, 'pending', :created_at, :updated_at)
            """)
            
            connection.execute(insert_query, {
                'job_type': job_type,
                'payload': json.dumps(update_data), # Store payload as a JSON string
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            # The connection context manager will automatically commit.
        
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