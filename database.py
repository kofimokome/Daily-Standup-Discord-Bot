"""
Database module for persistent storage of user commitments and responses.

Uses SQLite to store:
- Daily standup responses
- User commitments
- Follow-up tracking
"""

import sqlite3
import json
import os
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class Database:
    """Handles all database operations for the standup bot."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to the SQLite database file (defaults to DATABASE_PATH env var or 'standup_bot.db')
        """
        self.db_path = db_path or os.environ.get("DATABASE_PATH", "standup_bot.db")
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def init_database(self):
        """Create necessary tables if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Table for storing daily standup responses
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS standup_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                response_date DATE NOT NULL,
                today_work TEXT,
                tomorrow_commitment TEXT,
                raw_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, response_date)
            )
        """)
        
        # Table for tracking follow-up messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS follow_ups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                commitment_id INTEGER NOT NULL,
                commitment_date DATE NOT NULL,
                follow_up_sent BOOLEAN DEFAULT 0,
                follow_up_date DATE,
                completion_status TEXT,
                FOREIGN KEY (commitment_id) REFERENCES standup_responses(id)
            )
        """)
        
        # Table for storing bot configuration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def save_standup_response(
        self,
        user_id: int,
        username: str,
        message_id: int,
        response_date: date,
        today_work: Optional[str] = None,
        tomorrow_commitment: Optional[str] = None,
        raw_message: str = ""
    ) -> int:
        """
        Save a standup response to the database.
        
        Args:
            user_id: Discord user ID
            username: Discord username
            message_id: Discord message ID
            response_date: Date of the response
            today_work: What the user worked on today
            tomorrow_commitment: What the user committed to do tomorrow
            raw_message: Original message text
            
        Returns:
            ID of the inserted record
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO standup_responses 
                (user_id, username, message_id, response_date, today_work, tomorrow_commitment, raw_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, message_id, response_date, today_work, tomorrow_commitment, raw_message))
            
            response_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Saved standup response for user {user_id} on {response_date}")
            return response_id
        except Exception as e:
            logger.error(f"Error saving standup response: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_commitments_for_date(self, target_date: date) -> List[Dict]:
        """
        Get all commitments made on a specific date.
        
        Args:
            target_date: Date to get commitments for
            
        Returns:
            List of commitment records
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_id, username, tomorrow_commitment, response_date
            FROM standup_responses
            WHERE response_date = ? AND tomorrow_commitment IS NOT NULL AND tomorrow_commitment != ''
        """, (target_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

    def get_responses_for_date(self, target_date: date) -> List[Dict]:
        """
        Get all standup responses for a specific date.
        
        Args:
            target_date: Date to get responses for
            
        Returns:
            List of response records
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM standup_responses
            WHERE response_date = ?
        """, (target_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

    
    def get_pending_follow_ups(self, target_date: date) -> List[Dict]:
        """
        Get all commitments that need follow-up messages for a specific date.
        
        Args:
            target_date: Date to check for pending follow-ups
            
        Returns:
            List of commitments needing follow-up
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get commitments from yesterday that haven't been followed up yet
        cursor.execute("""
            SELECT sr.id, sr.user_id, sr.username, sr.tomorrow_commitment, sr.response_date
            FROM standup_responses sr
            LEFT JOIN follow_ups fu ON sr.id = fu.commitment_id
            WHERE sr.response_date = ? 
            AND sr.tomorrow_commitment IS NOT NULL 
            AND sr.tomorrow_commitment != ''
            AND (fu.id IS NULL OR fu.follow_up_sent = 0)
        """, (target_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def mark_follow_up_sent(self, commitment_id: int, follow_up_date: date):
        """
        Mark a follow-up message as sent.
        
        Args:
            commitment_id: ID of the commitment record
            follow_up_date: Date the follow-up was sent
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if follow-up record exists
        cursor.execute("SELECT id FROM follow_ups WHERE commitment_id = ?", (commitment_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("""
                UPDATE follow_ups 
                SET follow_up_sent = 1, follow_up_date = ?
                WHERE commitment_id = ?
            """, (follow_up_date, commitment_id))
        else:
            # Get the commitment to get user_id and response_date
            cursor.execute("""
                SELECT user_id, response_date FROM standup_responses WHERE id = ?
            """, (commitment_id,))
            commitment = cursor.fetchone()
            
            if commitment:
                # SQLite Row object supports dictionary-style access
                user_id = commitment['user_id']
                response_date = commitment['response_date']
                cursor.execute("""
                    INSERT INTO follow_ups 
                    (user_id, commitment_id, commitment_date, follow_up_sent, follow_up_date)
                    VALUES (?, ?, ?, 1, ?)
                """, (user_id, commitment_id, response_date, follow_up_date))
        
        conn.commit()
        conn.close()
        logger.info(f"Marked follow-up as sent for commitment {commitment_id}")
    
    def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM bot_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        
        return row['value'] if row else default
    
    def set_config(self, key: str, value: str):
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO bot_config (key, value)
            VALUES (?, ?)
        """, (key, value))
        
        conn.commit()
        conn.close()
        logger.info(f"Set config {key} = {value}")
    
    def get_user_responses(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Get recent responses for a specific user.
        
        Args:
            user_id: Discord user ID
            limit: Maximum number of responses to return
            
        Returns:
            List of user responses
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM standup_responses
            WHERE user_id = ?
            ORDER BY response_date DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

