# worker/telegram_helper.py

import os
import requests
import logging

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')

class TelegramHelper:
    def __init__(self, token=None):
        self.token = token or BOT_TOKEN
        if not self.token:
            raise ValueError("Telegram Bot Token is not configured.")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, chat_id, text, parse_mode=None, reply_markup=None):
        """Sends a text message."""
        payload = {'chat_id': chat_id, 'text': text}
        if parse_mode:
            payload['parse_mode'] = parse_mode
        if reply_markup:
            payload['reply_markup'] = reply_markup
        
        try:
            response = requests.post(f"{self.base_url}/sendMessage", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            return None

    def approve_chat_join_request(self, chat_id, user_id):
        """Approves a chat join request."""
        payload = {'chat_id': chat_id, 'user_id': user_id}
        try:
            response = requests.post(f"{self.base_url}/approveChatJoinRequest", json=payload)
            response.raise_for_status()
            logger.info(f"Approved join request for user {user_id} in chat {chat_id}.")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error approving join request for user {user_id} in chat {chat_id}: {e}")
            return None

    def get_me(self):
        """Gets the bot's own information."""
        try:
            response = requests.get(f"{self.base_url}/getMe")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error calling getMe: {e}")
            return None
