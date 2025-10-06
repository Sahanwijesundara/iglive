# create_test_job.py

import os
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file.")

# A sample Telegram payload for a /start command
SAMPLE_PAYLOAD = {
  "update_id": 10001, # Use a different ID to avoid duplicates
  "message": {
    "message_id": 1366,
    "from": {
      "id": 987654321,
      "is_bot": False,
      "first_name": "Local",
      "last_name": "Tester",
      "username": "localtester",
      "language_code": "en"
    },
    "chat": {
      "id": 987654321,
      "first_name": "Local",
      "last_name": "Tester",
      "username": "localtester",
      "type": "private"
    },
    "date": 1587403633,
    "text": "/start",
    "entities": [{ "offset": 0, "length": 6, "type": "bot_command" }]
  }
}

def create_test_job():
    """Connects to the database and inserts a new test job."""
    print("Connecting to the database...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            print("Connection successful. Inserting test job...")
            with connection.begin() as transaction:
                insert_query = text("""
                    INSERT INTO jobs (job_type, payload, status, created_at, updated_at)
                    VALUES (:job_type, :payload, 'pending', :created_at, :updated_at)
                """)
                connection.execute(insert_query, {
                    'job_type': 'process_telegram_update',
                    'payload': json.dumps(SAMPLE_PAYLOAD),
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                })
                transaction.commit()
            print("[SUCCESS] Test job created successfully!")
            print("You can now run the worker to process it.")

    except Exception as e:
        print(f"[FAILURE] An error occurred: {e}")

if __name__ == "__main__":
    create_test_job()