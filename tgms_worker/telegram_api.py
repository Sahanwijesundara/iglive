"""
Simplified Telegram API handler for TGMS worker
"""
import requests
import logging
import time

logger = logging.getLogger(__name__)


class TelegramAPI:
    """Simple Telegram Bot API wrapper"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session = requests.Session()
    
    def _request(self, method: str, **kwargs):
        """Make API request with error handling"""
        url = f"{self.base_url}/{method}"
        try:
            response = self.session.post(url, json=kwargs, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {method} - {e}")
            return {"ok": False, "error": str(e)}
    
    def send_message(self, chat_id: int, text: str, **kwargs):
        """Send text message"""
        return self._request("sendMessage", chat_id=chat_id, text=text, **kwargs)
    
    def send_photo(self, chat_id: int, photo: str, **kwargs):
        """Send photo"""
        return self._request("sendPhoto", chat_id=chat_id, photo=photo, **kwargs)
    
    def approve_join_request(self, chat_id: int, user_id: int):
        """Approve chat join request"""
        return self._request("approveChatJoinRequest", chat_id=chat_id, user_id=user_id)
    
    def decline_join_request(self, chat_id: int, user_id: int):
        """Decline chat join request"""
        return self._request("declineChatJoinRequest", chat_id=chat_id, user_id=user_id)
    
    def kick_member(self, chat_id: int, user_id: int):
        """Kick (ban) member from chat"""
        return self._request("banChatMember", chat_id=chat_id, user_id=user_id)
    
    def get_chat_members_count(self, chat_id: int):
        """Get member count (uses getChatMemberCount with fallback)"""
        result = self._request("getChatMemberCount", chat_id=chat_id)
        if not result.get("ok"):
            # Fallback to legacy/misspelled variant if any
            result = self._request("getChatMembersCount", chat_id=chat_id)
        return result.get("result", 0) if result.get("ok") else 0
    
    def delete_message(self, chat_id: int, message_id: int):
        """Delete message"""
        return self._request("deleteMessage", chat_id=chat_id, message_id=message_id)
