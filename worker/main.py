# worker/main.py

import os
import json
import logging
import asyncio
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from handlers import (
    start_handler,
    my_account_handler,
    check_live_handler,
    join_request_handler,
    broadcast_message_handler,
    init_handler,
    activate_handler,
    back_handler,
)

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

POLLING_INTERVAL = 2 # seconds

async def process_job(job, session_factory):
    """
    Processes a job from the queue by routing it to the appropriate handler.
    """
    job_id = job['job_id']
    job_type = job['job_type']
    payload_data = job.get('payload', '{}')

    # Safely parse the JSON payload
    try:
        if isinstance(payload_data, str):
            payload = json.loads(payload_data)
        elif isinstance(payload_data, dict):
            payload = payload_data
        else:
            logger.error(f"Payload for job_id: {job_id} is not a dict or a valid JSON string.")
            return False
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Invalid JSON payload for job_id: {job_id}. Payload: {payload_data}, Error: {e}")
        return False

    logger.info(f"Processing job_id: {job_id} of type: {job_type}")
    session = session_factory()

    try:
        if job_type == 'process_telegram_update':
            if 'message' in payload:
                text = payload['message'].get('text', '').strip()
                if text.startswith('/start'):
                    await start_handler(session, payload)
                elif text.startswith('/init'):
                    await init_handler(session, payload)
                elif text.startswith('/activate'):
                    await activate_handler(session, payload)
            elif 'callback_query' in payload:
                callback_data = payload['callback_query'].get('data')
                if callback_data == 'my_account':
                    await my_account_handler(session, payload)
                elif callback_data == 'check_live':
                    await check_live_handler(session, payload)
                elif callback_data == 'back':
                    await back_handler(session, payload)
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

        return True
    except Exception as e:
        logger.error(f"A handler raised an exception for job {job_id}: {e}", exc_info=True)
        return False # Explicitly return False on error
    finally:
        session.close()

async def worker_main_loop(session_factory, run_once=False):
    """
    The main loop for the worker.
    - Fetches a pending job from the database.
    - Marks it as 'processing'.
    - Calls process_job to handle it.
    - Updates the job status based on the result.
    """
    run_once_retries = 0
    while True:
        job_to_process = None
        session = session_factory()
        try:
            # --- 1. Fetch and Lock a Job ---
            select_query = text("""
                SELECT * FROM jobs
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """)
            result = session.execute(select_query).fetchone()

            if result:
                job_to_process = dict(result._mapping)
                update_query = text("""
                    UPDATE jobs
                    SET status = 'processing', updated_at = :now
                    WHERE job_id = :job_id
                """)
                session.execute(update_query, {'now': datetime.now(timezone.utc), 'job_id': job_to_process['job_id']})
                session.commit()
                logger.info(f"Locked and picked up job_id: {job_to_process['job_id']}")

            # --- 2. Process the Job ---
            if job_to_process:
                success = await process_job(job_to_process, session_factory)
                
                # --- 3. Update Job Status ---
                retries = job_to_process.get('retries', 0)
                if success:
                    final_status = 'completed'
                else:
                    if retries < 3:
                        final_status = 'pending' # Put it back in the queue for another try
                    else:
                        final_status = 'failed'

                update_query = text("""
                    UPDATE jobs
                    SET status = :status, retries = :retries, updated_at = :now
                    WHERE job_id = :job_id
                """)
                session.execute(update_query, {
                    'status': final_status,
                    'retries': retries + 1 if not success else retries,
                    'now': datetime.now(timezone.utc),
                    'job_id': job_to_process['job_id']
                })
                session.commit()
                logger.info(f"Job {job_to_process['job_id']} finished with status: {final_status}")
                
                if run_once:
                    logger.info("run_once is True, exiting after processing one job.")
                    break
            else:
                if run_once:
                    if run_once_retries >= 2: # Try up to 3 times (0, 1, 2)
                        logger.info("run_once is True, exiting worker loop after multiple attempts.")
                        break
                    run_once_retries += 1
                    logger.info(f"run_once mode: No job found, retrying... (Attempt {run_once_retries})")
                    await asyncio.sleep(1) # Wait a bit for the transaction to commit
                    continue

                await asyncio.sleep(POLLING_INTERVAL)

        except Exception as e:
            logger.error(f"Error in worker main loop: {e}", exc_info=True)
            if session.is_active:
                session.rollback()
            await asyncio.sleep(POLLING_INTERVAL * 2)
        finally:
            session.close()


def main(run_once=False, engine=None):
    # If no engine is passed, create one (for standalone execution)
    if engine is None:
        # Correctly load the .env file from the parent directory
        dotenv_path = os.path.join(os.path.dirname(__file__), '../.env')
        load_dotenv(dotenv_path=dotenv_path)

        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not found in environment.")

        try:
            engine = create_engine(DATABASE_URL)
            logger.info("Database engine created successfully.")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}", exc_info=True)
            exit(1)
            
    # Create a session factory from the (potentially shared) engine
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Session factory created.")

    logger.info("Starting worker process...")
    
    # Start Instagram checker as background task if not in run_once mode
    if not run_once:
        try:
            from instagram_checker import start_instagram_checker
            logger.info("Starting Instagram live checker background task...")
            # This will be run concurrently with the main worker loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ig_task = loop.create_task(start_instagram_checker(SessionFactory)())
            worker_task = loop.create_task(worker_main_loop(SessionFactory, run_once=run_once))
            
            try:
                loop.run_until_complete(asyncio.gather(ig_task, worker_task))
            except KeyboardInterrupt:
                logger.info("Worker process stopped by user.")
                ig_task.cancel()
                worker_task.cancel()
            finally:
                loop.close()
        except ImportError:
            logger.warning("Instagram checker not available. Running without live tracking.")
            asyncio.run(worker_main_loop(SessionFactory, run_once=run_once))
    else:
        try:
            asyncio.run(worker_main_loop(SessionFactory, run_once=run_once))
        except KeyboardInterrupt:
            logger.info("Worker process stopped by user.")

if __name__ == '__main__':
    main()