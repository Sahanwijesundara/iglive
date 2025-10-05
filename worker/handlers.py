# worker/handlers.py

import os
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from telethon import TelegramClient

from models import TelegramUser
from telegram_helper import TelegramHelper

# --- Logging Setup ---
logger = logging.getLogger(__name__)

# --- Constants ---
# In a real app, these would come from a config file
BOT_TOKEN = os.environ.get('BOT_TOKEN')
BOT_API_ID = os.environ.get('BOT_API_ID')
BOT_API_HASH = os.environ.get('BOT_API_HASH')


def is_new_day_for_user(user: TelegramUser) -> bool:
    """Check if it's a new day for the user considering timezone."""
    if not user.last_seen:
        return True
    
    now = datetime.now(timezone.utc)
    last_seen_utc = user.last_seen.replace(tzinfo=timezone.utc) if user.last_seen.tzinfo is None else user.last_seen
    
    # Simple daily reset at UTC midnight
    return now.date() > last_seen_utc.date()

async def send_user_feedback(user_id: int, message: str):
    """Send feedback to user with error handling."""
    # This requires a Telegram client. For the worker, we can create a
    # short-lived client or use a helper that sends via Bot API.
    # For now, this is a placeholder.
    logger.info(f"FEEDBACK to {user_id}: {message}")
    # In a real implementation:
    # async with TelegramClient('worker_session', BOT_API_ID, BOT_API_HASH) as client:
    #     await client.send_message(user_id, message)


async def start_handler(session: Session, payload: dict):
    """
    Handles the logic for a /start command from a user.
    This function is called by the worker when it processes a 'start_command' job.
    """
    try:
        message = payload.get('message', {})
        from_user = message.get('from', {})
        sender_id = from_user.get('id')
        
        if not sender_id:
            logger.error("Could not determine sender_id from payload.")
            return

        user = session.query(TelegramUser).filter_by(id=sender_id).first()
        
        prefix_message = ""
        if not user:
            # --- Handle New User & Referrals ---
            referred_by_id = None
            text = message.get('text', '')
            if text and len(text.split()) > 1:
                try:
                    referred_by_id = int(text.split()[1])
                    if referred_by_id == sender_id: # Can't refer self
                        referred_by_id = None
                except (ValueError, IndexError):
                    referred_by_id = None

            user = TelegramUser(
                id=sender_id,
                username=from_user.get('username'),
                first_name=from_user.get('first_name'),
                points=10,
                last_seen=datetime.now(timezone.utc),
                referred_by_id=referred_by_id
            )
            session.add(user)
            session.commit()
            prefix_message = f"Welcome, {user.first_name}! You have been given 10 points.\n\n"
            logger.info(f"New user created: {user.id} (@{user.username})")

            if referred_by_id:
                referrer = session.query(TelegramUser).filter_by(id=referred_by_id).first()
                if referrer:
                    referrer.points += 10
                    session.commit()
                    await send_user_feedback(
                        referrer.id,
                        f"🎉 {user.first_name} joined using your referral link! You've earned 10 points."
                    )
                    logger.info(f"Awarded 10 referral points to {referrer.id}")

        elif is_new_day_for_user(user):
            # --- Handle Daily Point Reset ---
            user.points = 10
            user.last_seen = datetime.now(timezone.utc)
            session.commit()
            prefix_message = "Your points have been reset to 10 for the day!\n\n"
            logger.info(f"Reset daily points for user {user.id}")

        # --- Send Main Menu ---
        # In the worker, instead of sending a menu directly, we might enqueue
        # another job for the bot to send a message. For now, we'll just log it.
        logger.info(f"Should send main menu to {user.id} with prefix: '{prefix_message}'")
        # Example of sending a response (would be implemented with a Telegram helper)
        # await send_main_menu(user.id, message_text=prefix_message + "🎉 Welcome to InstaLive Pro! 🎉")

    except Exception as e:
        logger.error(f"Error in start_handler for user {sender_id}: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()


async def my_account_handler(session: Session, payload: dict):
    """
    Handles the logic for a /my_account command from a user.
    """
    try:
        callback_query = payload.get('callback_query', {})
        from_user = callback_query.get('from', {})
        sender_id = from_user.get('id')

        if not sender_id:
            logger.error("Could not determine sender_id from payload.")
            return

        user = session.query(TelegramUser).filter_by(id=sender_id).first()
        if not user:
            # In a real app, send a message back. For now, just log.
            logger.warning(f"User {sender_id} not found for my_account.")
            return

        # This is where you would format a message with the user's account details
        # and then enqueue another job to send that message.
        logger.info(f"Account details for user {user.id}: Points={user.points}, SubscribedUntil={user.subscription_end}")
        # e.g., await enqueue_message_job(user.id, formatted_message)

    except Exception as e:
        logger.error(f"Error in my_account_handler for user {sender_id}: {e}", exc_info=True)
    finally:
        session.close()


async def check_live_handler(session: Session, payload: dict):
    """
    Handles the logic for a /check_live command from a user.
    """
    try:
        callback_query = payload.get('callback_query', {})
        from_user = callback_query.get('from', {})
        sender_id = from_user.get('id')

        if not sender_id:
            logger.error("Could not determine sender_id from payload.")
            return

        user = session.query(TelegramUser).filter_by(id=sender_id).first()
        if not user:
            logger.warning(f"User {sender_id} not found for check_live.")
            return

        # Deduct points if not unlimited
        is_unlimited = user.subscription_end and user.subscription_end > datetime.now(timezone.utc)
        if not is_unlimited:
            if user.points > 0:
                user.points -= 1
                session.commit()
            else:
                logger.info(f"User {user.id} has no points to check live users.")
                # Enqueue a "no points" message job
                return
        
        # In a real app, you would query the `insta_links` table for live users,
        # format a paginated message, and enqueue a job to send it.
        logger.info(f"User {user.id} checked for live users. Points remaining: {user.points}")

    except Exception as e:
        logger.error(f"Error in check_live_handler for user {sender_id}: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()


async def join_request_handler(session: Session, payload: dict):
    """
    Handles a chat_join_request update from Telegram.
    """
    try:
        join_request = payload.get('chat_join_request', {})
        chat = join_request.get('chat', {})
        user = join_request.get('from', {})
        
        chat_id = chat.get('id')
        user_id = user.get('id')

        if not chat_id or not user_id:
            logger.error("Could not determine chat_id or user_id from join request payload.")
            return

        # For the MVP, we will auto-approve join requests.
        # A more advanced implementation would check rules from the `tele_group_management_system.py`.
        helper = TelegramHelper()
        helper.approve_chat_join_request(chat_id, user_id)

        # Log the action to the database
        # (This part would be built out more in a full implementation)
        logger.info(f"Auto-approved join request for user {user_id} in chat {chat_id}.")

    except Exception as e:
        logger.error(f"Error in join_request_handler: {e}", exc_info=True)
    finally:
        session.close()


async def broadcast_message_handler(session: Session, payload: dict):
    """
    Handles a broadcast_message job, sending a message to all active groups.
    """
    try:
        message_text = payload.get('text')
        if not message_text:
            logger.error("Broadcast job is missing 'text' in payload.")
            return

        # In a real app, you'd get this from a 'managed_groups' table.
        # For the MVP, we can hardcode a list or fetch from ChatGroup.
        active_groups = session.query(ChatGroup).filter_by(is_active=True).all()
        
        if not active_groups:
            logger.info("No active groups to broadcast to.")
            return

        helper = TelegramHelper()
        for group in active_groups:
            try:
                chat_id = int(group.chat_id)
                helper.send_message(chat_id, message_text)
                logger.info(f"Broadcasted message to group {chat_id}.")
                # Implement rate limiting
                await asyncio.sleep(1) # Simple 1-second delay between messages
            except ValueError:
                logger.warning(f"Could not convert chat_id '{group.chat_id}' to int. Skipping.")
            except Exception as e:
                logger.error(f"Failed to broadcast to group {group.chat_id}: {e}")

    except Exception as e:
        logger.error(f"Error in broadcast_message_handler: {e}", exc_info=True)
    finally:
        session.close()