# worker/main.py

import os
import json
import logging
import time
from datetime import datetime, timedelta, timezone
import traceback
import asyncio

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from handlers import (
    start_handler, my_account_handler, check_live_handler,
    join_request_handler, broadcast_message_handler
)
from models import Base

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constants ---
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.warning("DATABASE_URL environment variable not set. Using a default local fallback.")
    DATABASE_URL = "postgresql://user:password@host:port/database"

POLL_INTERVAL_SECONDS = 2  # Time to wait between polling for new jobs
MAX_RETRIES = 3
JOB_TIMEOUT_MINUTES = 10 # Time after which a 'processing' job is considered stale

# --- Database Connection ---
def get_db_engine():
    """Creates and returns a new SQLAlchemy engine."""
    try:
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(engine)
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}", exc_info=True)
        return None

async def process_job(job, session_factory):
    """
    Processes a job from the queue by routing it to the appropriate handler.
    """
    job_id = job['job_id']
    job_type = job['job_type']
    payload_str = job.get('payload', '{}')

    # Safely parse the JSON payload
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON payload for job_id: {job_id}. Payload: {payload_str}")
        # Mark as failed to prevent retries of a malformed job
        return False

    logger.info(f"Processing job_id: {job_id} of type: {job_type}")
    session = session_factory()

    try:
        if job_type == 'process_telegram_update':
            if 'message' in payload and payload['message'].get('text', '').strip().startswith('/start'):
                await start_handler(session, payload)
            elif 'callback_query' in payload:
                callback_data = payload['callback_query'].get('data')
                if callback_data == 'my_account':
                    await my_account_handler(session, payload)
                elif callback_data == 'check_live':
                    await check_live_handler(session, payload)
                else:
                    logger.info(f"No handler for callback_data: '{callback_data}'")
            elif 'chat_join_request' in payload:
                await join_request_handler(session, payload)
            else:
                logger.info(f"No handler for this update type.")
        
        elif job_type == 'broadcast_message':
            await broadcast_message_handler(session, payload)

        else:
            logger.warning(f"Unknown job_type: {job_type}")

        return True  # Assume success to prevent retries for unhandled types
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
        return False # Explicitly return False on error
    finally:
        session.close()

async def poll_for_jobs():
    """The main loop for the worker process."""
    engine = get_db_engine()
    if not engine:
        logger.critical("Worker cannot start without a database connection.")
        return

    Session = sessionmaker(bind=engine)
    logger.info("Worker started. Polling for jobs...")

    while True:
        job = None
        try:
            with engine.connect() as connection:
                # Atomically fetch a pending job and update its status to 'processing'
                stale_time = datetime.now(timezone.utc) - timedelta(minutes=JOB_TIMEOUT_MINUTES)
                claim_query = text("""
                    WITH next_job AS (
                        SELECT job_id FROM jobs
                        WHERE (status = 'pending' OR (status = 'processing' AND updated_at < :stale_time))
                          AND retries < :max_retries
                        ORDER BY created_at
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE jobs SET status = 'processing', updated_at = :now
                    WHERE job_id = (SELECT job_id FROM next_job)
                    RETURNING job_id, job_type, payload, retries;
                """)
                result = connection.execute(claim_query, {
                    'stale_time': stale_time,
                    'max_retries': MAX_RETRIES,
                    'now': datetime.now(timezone.utc)
                }).fetchone()

                if result:
                    # Manually construct a dictionary from the row object
                    job = {
                        'job_id': result[0],
                        'job_type': result[1],
                        'payload': result[2],
                        'retries': result[3]
                    }
                    logger.info(f"Claimed job_id: {job['job_id']}")

            # Process the job outside the main transaction to avoid holding locks
            if job:
                try:
                    success = await process_job(job, Session)
                    with engine.connect() as update_connection:
                        if success:
                            update_query = text("UPDATE jobs SET status = 'completed', updated_at = :now WHERE job_id = :job_id")
                            update_connection.execute(update_query, {'now': datetime.now(timezone.utc), 'job_id': job['job_id']})
                            logger.info(f"Job {job['job_id']} completed successfully.")
                        else:
                            # This case is for when process_job explicitly returns False
                            raise RuntimeError(f"Job {job['job_id']} failed during processing.")
                except Exception as processing_error:
                    logger.error(f"Error processing job {job['job_id']}: {processing_error}", exc_info=True)
                    with engine.connect() as error_connection:
                        update_query = text("UPDATE jobs SET status = 'failed', retries = retries + 1, updated_at = :now WHERE job_id = :job_id")
                        error_connection.execute(update_query, {'now': datetime.now(timezone.utc), 'job_id': job['job_id']})
                        logger.warning(f"Job {job['job_id']} failed. Retry count is now {job['retries'] + 1}.")
            else:
                # No jobs found, sleep asynchronously
                await asyncio.sleep(POLL_INTERVAL_SECONDS)

        except OperationalError as e:
            logger.error(f"Database connection error: {e}. Reconnecting...", exc_info=True)
            await asyncio.sleep(10)
            engine = get_db_engine()
        except Exception as e:
            logger.error(f"An unexpected error occurred in the polling loop: {e}", exc_info=True)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == '__main__':
    asyncio.run(poll_for_jobs())