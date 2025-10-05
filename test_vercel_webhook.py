# test_vercel_webhook.py

import requests
import json

# --- Configuration ---
# Your Vercel deployment URL
VERCEL_URL = "https://iglive-z5op.vercel.app/api/webhook"

# A sample Telegram payload for a /start command
SAMPLE_PAYLOAD = {
  "update_id": 10000,
  "message": {
    "message_id": 1365,
    "from": {
      "id": 123456789,
      "is_bot": False,
      "first_name": "Test",
      "last_name": "User",
      "username": "testuser",
      "language_code": "en"
    },
    "chat": {
      "id": 123456789,
      "first_name": "Test",
      "last_name": "User",
      "username": "testuser",
      "type": "private"
    },
    "date": 1587403632,
    "text": "/start",
    "entities": [{ "offset": 0, "length": 6, "type": "bot_command" }]
  }
}

def test_webhook():
    """
    Sends a POST request to the Vercel webhook endpoint to simulate a Telegram update.
    """
    print(f"Sending test payload to: {VERCEL_URL}")
    
    try:
        response = requests.post(VERCEL_URL, json=SAMPLE_PAYLOAD, timeout=10)
        
        # Print the response from the server
        print(f"\nStatus Code: {response.status_code}")
        print("Response JSON:")
        try:
            print(json.dumps(response.json(), indent=2))
        except json.JSONDecodeError:
            print(response.text)

        if response.status_code == 200:
            print("\n[SUCCESS] Test Passed: The server responded with 200 OK.")
            print("Check your Supabase 'jobs' table for a new entry.")
        else:
            print(f"\n[FAILURE] Test Failed: The server responded with status code {response.status_code}.")
            print("Check the Vercel logs for more details about the error.")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ An error occurred while sending the request: {e}")

if __name__ == "__main__":
    test_webhook()