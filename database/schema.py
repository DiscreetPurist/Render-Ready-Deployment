import logging
from config.database import db_config

def create_tables():
    """Create all necessary database tables"""
    
    # Users table with email and password fields added
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        user_id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        number VARCHAR(20) UNIQUE NOT NULL,
        location VARCHAR(255) NOT NULL,
        range_miles INTEGER NOT NULL,
        stripe_customer_id VARCHAR(255) UNIQUE,
        subscription_id VARCHAR(255) UNIQUE,
        active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Index for faster lookups
    create_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
        "CREATE INDEX IF NOT EXISTS idx_users_number ON users(number);",
        "CREATE INDEX IF NOT EXISTS idx_users_stripe_customer ON users(stripe_customer_id);",
        "CREATE INDEX IF NOT EXISTS idx_users_active ON users(active);",
        "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);"
    ]
    
    # Message cache table (optional - for duplicate detection)
    create_message_cache_table = """
    CREATE TABLE IF NOT EXISTS message_cache (
        id SERIAL PRIMARY KEY,
        message_hash VARCHAR(64) UNIQUE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Auto-cleanup old cache entries
    create_cleanup_function = """
    CREATE OR REPLACE FUNCTION cleanup_old_messages()
    RETURNS void AS $$
    BEGIN
        DELETE FROM message_cache 
        WHERE created_at < NOW() - INTERVAL '24 hours';
    END;
    $$ LANGUAGE plpgsql;
    """
    
    try:
        with db_config.get_connection() as conn:
            with conn.cursor() as cursor:
                # Create tables
                cursor.execute(create_users_table)
                cursor.execute(create_message_cache_table)
                cursor.execute(create_cleanup_function)
                
                # Create indexes
                for index_sql in create_indexes:
                    cursor.execute(index_sql)
                
                conn.commit()
                logging.info("Database schema created successfully")
                
    except Exception as e:
        logging.error(f"Error creating database schema: {e}")
        raise

def initialize_database():
    """Initialize database with schema and test connection"""
    try:
        # Test connection first
        if not db_config.test_connection():
            raise Exception("Database connection test failed")
        
        # Create schema
        create_tables()
        
        logging.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        return False
