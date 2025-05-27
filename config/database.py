import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from urllib.parse import urlparse

class DatabaseConfig:
    """Database configuration and connection management"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Parse the database URL
        self.parsed_url = urlparse(self.database_url)
        
    def get_connection(self):
        """Get a database connection"""
        try:
            # Use the full DATABASE_URL for connection
            conn = psycopg2.connect(self.database_url)
            return conn
        except psycopg2.Error as e:
            logging.error(f"Database connection failed: {e}")
            raise
    
    def test_connection(self):
        """Test database connectivity"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()
                    logging.info(f"Connected to PostgreSQL: {version[0]}")
                    return True
        except Exception as e:
            logging.error(f"Database connection test failed: {e}")
            return False

# Global database config instance
db_config = DatabaseConfig()
