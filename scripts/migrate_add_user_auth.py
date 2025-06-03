#!/usr/bin/env python3
"""
Database migration script to add email and password_hash columns to users table
Run this script to update existing databases with the new authentication fields
"""

import os
import sys
import logging
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import db_config

def migrate_database():
    """Add email and password_hash columns to users table"""
    
    migration_queries = [
        # Add email column if it doesn't exist
        """
        DO $$ 
        BEGIN 
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'email'
            ) THEN
                ALTER TABLE users ADD COLUMN email VARCHAR(255);
            END IF;
        END $$;
        """,
        
        # Add password_hash column if it doesn't exist
        """
        DO $$ 
        BEGIN 
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'password_hash'
            ) THEN
                ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);
            END IF;
        END $$;
        """,
        
        # Create index on email if it doesn't exist
        """
        DO $$ 
        BEGIN 
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'users' AND indexname = 'idx_users_email'
            ) THEN
                CREATE INDEX idx_users_email ON users(email);
            END IF;
        END $$;
        """,
        
        # Make email unique if there are no duplicates
        """
        DO $$ 
        BEGIN 
            -- Only add unique constraint if email column exists and has no duplicates
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'email'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE table_name = 'users' AND constraint_name = 'users_email_key'
            ) THEN
                -- Check for duplicates first
                IF (SELECT COUNT(*) FROM (
                    SELECT email FROM users WHERE email IS NOT NULL 
                    GROUP BY email HAVING COUNT(*) > 1
                ) AS duplicates) = 0 THEN
                    ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);
                ELSE
                    RAISE NOTICE 'Cannot add unique constraint on email - duplicates exist';
                END IF;
            END IF;
        END $$;
        """
    ]
    
    try:
        with db_config.get_connection() as conn:
            with conn.cursor() as cursor:
                for i, query in enumerate(migration_queries, 1):
                    try:
                        logging.info(f"Running migration step {i}...")
                        cursor.execute(query)
                        conn.commit()
                        logging.info(f"Migration step {i} completed successfully")
                    except Exception as e:
                        logging.error(f"Error in migration step {i}: {e}")
                        conn.rollback()
                        # Continue with other steps
                        continue
                
                # Check final table structure
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'users'
                    ORDER BY ordinal_position;
                """)
                
                columns = cursor.fetchall()
                logging.info("Final table structure:")
                for col in columns:
                    logging.info(f"  {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
                
        logging.info("Database migration completed successfully!")
        return True
        
    except Exception as e:
        logging.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("Starting database migration...")
    print("This will add email and password_hash columns to the users table.")
    
    if migrate_database():
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed. Check the logs for details.")
        sys.exit(1)
