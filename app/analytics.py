import sqlite3
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

class AnalyticsDB:
    def __init__(self):
        """Initialize the analytics database with environment-aware path selection."""
        # Determine environment and set appropriate database path
        environment = os.environ.get('ENVIRONMENT', 'dev')
        
        if environment == 'prod':
            # Use Render disk mount for production
            disk_path = os.environ.get('RENDER_DISK_PATH', '/videoAnalytics')
            os.makedirs(disk_path, exist_ok=True)  # Ensure directory exists
            self.db_path = os.path.join(disk_path, 'analytics.db')
            logging.info(f"Using production database at {self.db_path}")
        else:
            # Use local path for development
            self.db_path = 'analytics.db'
            logging.info(f"Using local database at {self.db_path}")
        
        # Initialize the database
        self._initialize_db()
        
    def _initialize_db(self):
        """Create the analytics table if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create analytics table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                video_id TEXT NOT NULL,
                video_title TEXT NOT NULL,
                origin TEXT NOT NULL,
                status TEXT NOT NULL,
                claim_count INTEGER,
                input_tokens INTEGER,
                output_tokens INTEGER,
                processing_time_ms INTEGER,
                error_message TEXT
            )
            ''')
            
            # Create indexes for common queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON video_analytics(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_id ON video_analytics(video_id)')
            
            conn.commit()
            conn.close()
            logging.info("Analytics database initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing analytics database: {e}")
            
    def log_video_processing(self, 
                           video_id: str,
                           video_title: str,
                           origin: str,
                           status: str,
                           claim_count: Optional[int] = None,
                           input_tokens: Optional[int] = None,
                           output_tokens: Optional[int] = None,
                           processing_time_ms: Optional[int] = None,
                           error_message: Optional[str] = None):
        """Log video processing analytics to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO video_analytics (
                timestamp, video_id, video_title, origin, status, 
                claim_count, input_tokens, output_tokens, 
                processing_time_ms, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(timezone.utc).isoformat(),
                video_id,
                video_title,
                origin,
                status,
                claim_count,    
                input_tokens,
                output_tokens,
                processing_time_ms,
                error_message
            ))
            
            conn.commit()
            conn.close()
            logging.info(f"Logged analytics for video {video_id}")
        except Exception as e:
            logging.error(f"Error logging analytics: {e}")
            
    def get_recent_videos(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get the most recent video processing records."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM video_analytics
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (limit,))
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception as e:
            logging.error(f"Error retrieving analytics: {e}")
            return []