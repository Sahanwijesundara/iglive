"""
Database adapter for TGMS - Supabase PostgreSQL
Replaces SQLite-based DatabaseManager with PostgreSQL
"""
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


class DatabaseManager:
    """PostgreSQL Database Manager for TGMS"""
    
    def __init__(self, database_url: str):
        """
        Initialize database connection to Supabase PostgreSQL
        
        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        
        # Create engine with connection pooling
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        
        # Create session factory
        self.SessionFactory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info("DatabaseManager initialized with PostgreSQL connection pool")
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_connection(self):
        """Context manager for raw connections (for SQLite compatibility)"""
        connection = self.engine.connect()
        try:
            yield connection
        finally:
            connection.close()
    
    # --- Managed Groups Operations ---
    
    def get_active_managed_groups(self) -> List[Dict[str, Any]]:
        """Get all active managed groups"""
        with self.get_connection() as conn:
            result = conn.execute(text("""
                SELECT group_id, title, admin_user_id, phase, 
                       final_message_allowed, member_count, is_active
                FROM managed_groups
                WHERE is_active = true
                ORDER BY group_id
            """))
            return [dict(row._mapping) for row in result.fetchall()]
    
    def get_managed_group(self, group_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific managed group by ID"""
        with self.get_connection() as conn:
            result = conn.execute(
                text("SELECT * FROM managed_groups WHERE group_id = :group_id"),
                {"group_id": group_id}
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None
    
    def update_group_phase(self, group_id: int, phase: str):
        """Update group phase (growth/monitoring)"""
        with self.get_connection() as conn:
            conn.execute(
                text("""
                    UPDATE managed_groups 
                    SET phase = :phase, updated_at = NOW()
                    WHERE group_id = :group_id
                """),
                {"phase": phase, "group_id": group_id}
            )
            conn.commit()
    
    def update_member_count(self, group_id: int, count: int):
        """Update group member count"""
        with self.get_connection() as conn:
            conn.execute(
                text("""
                    UPDATE managed_groups 
                    SET member_count = :count, updated_at = NOW()
                    WHERE group_id = :group_id
                """),
                {"count": count, "group_id": group_id}
            )
            conn.commit()
    
    def deactivate_group(self, group_id: int, reason: str = None):
        """Deactivate a managed group"""
        with self.get_connection() as conn:
            conn.execute(
                text("""
                    UPDATE managed_groups 
                    SET is_active = false, updated_at = NOW()
                    WHERE group_id = :group_id
                """),
                {"group_id": group_id}
            )
            conn.commit()
            logger.info(f"Deactivated group {group_id}. Reason: {reason}")
    
    def increment_failure_count(self, group_id: int) -> int:
        """Increment consecutive failure count and return new count"""
        with self.get_connection() as conn:
            result = conn.execute(
                text("""
                    UPDATE managed_groups 
                    SET consecutive_failures = COALESCE(consecutive_failures, 0) + 1,
                        updated_at = NOW()
                    WHERE group_id = :group_id
                    RETURNING consecutive_failures
                """),
                {"group_id": group_id}
            )
            conn.commit()
            row = result.fetchone()
            return row[0] if row else 0
    
    def reset_failure_count(self, group_id: int):
        """Reset consecutive failure count to 0"""
        with self.get_connection() as conn:
            conn.execute(
                text("""
                    UPDATE managed_groups 
                    SET consecutive_failures = 0, updated_at = NOW()
                    WHERE group_id = :group_id
                """),
                {"group_id": group_id}
            )
            conn.commit()
    
    # --- Join Requests Operations ---
    
    def get_pending_join_requests(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get pending join requests"""
        with self.get_connection() as conn:
            result = conn.execute(
                text("""
                    SELECT request_id, user_id, chat_id, username, status, created_at
                    FROM join_requests
                    WHERE status = 'pending'
                    ORDER BY created_at
                    LIMIT :limit
                """),
                {"limit": limit}
            )
            return [dict(row._mapping) for row in result.fetchall()]
    
    def insert_join_request(self, user_id: int, chat_id: int, username: str = None):
        """Insert a new join request (with deduplication)"""
        with self.get_connection() as conn:
            try:
                conn.execute(
                    text("""
                        INSERT INTO join_requests (user_id, chat_id, username, status, created_at)
                        VALUES (:user_id, :chat_id, :username, 'pending', NOW())
                        ON CONFLICT (user_id, chat_id, status) DO NOTHING
                    """),
                    {"user_id": user_id, "chat_id": chat_id, "username": username}
                )
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not insert join request: {e}")
    
    def update_join_request_status(self, request_id: int, status: str):
        """Update join request status"""
        with self.get_connection() as conn:
            conn.execute(
                text("""
                    UPDATE join_requests 
                    SET status = :status
                    WHERE request_id = :request_id
                """),
                {"status": status, "request_id": request_id}
            )
            conn.commit()

    def update_join_request_status_by_user_chat(self, user_id: int, chat_id: int, status: str):
        """Update join request status using user_id and chat_id (latest pending)."""
        with self.get_connection() as conn:
            conn.execute(
                text("""
                    UPDATE join_requests
                    SET status = :status
                    WHERE user_id = :user_id AND chat_id = :chat_id AND status = 'pending'
                """),
                {"status": status, "user_id": user_id, "chat_id": chat_id}
            )
            conn.commit()
    
    # --- Sent Messages Tracking ---
    
    def log_sent_message(self, chat_id: int, telegram_message_id: int, debug_code: str):
        """Log a sent message"""
        with self.get_connection() as conn:
            conn.execute(
                text("""
                    INSERT INTO sent_messages (chat_id, telegram_message_id, debug_code, sent_at)
                    VALUES (:chat_id, :telegram_message_id, :debug_code, NOW())
                """),
                {"chat_id": chat_id, "telegram_message_id": telegram_message_id, "debug_code": debug_code}
            )
            conn.commit()
    
    # --- Bot Health Tracking ---
    
    def update_bot_health(self, bot_name: str, status: str, last_activity: str = None):
        """Update bot health status"""
        with self.get_connection() as conn:
            conn.execute(
                text("""
                    INSERT INTO bot_health (bot_name, status, last_activity, updated_at)
                    VALUES (:bot_name, :status, :last_activity, NOW())
                    ON CONFLICT (bot_name) DO UPDATE SET
                        status = EXCLUDED.status,
                        last_activity = EXCLUDED.last_activity,
                        updated_at = NOW()
                """),
                {"bot_name": bot_name, "status": status, "last_activity": last_activity}
            )
            conn.commit()
    
    def close(self):
        """Close database connections"""
        self.engine.dispose()
        logger.info("Database connections closed")
