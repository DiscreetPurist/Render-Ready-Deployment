import logging
from config.database import db_config

def create_tables():
    """Create all necessary database tables"""
    
    # First, check if users table exists and what columns it has
    check_table_query = """
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'users'
    ORDER BY ordinal_position;
    """
    
    try:
        with db_config.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(check_table_query)
                existing_columns = [row[0] for row in cursor.fetchall()]
                
                has_email = 'email' in existing_columns
                has_password_hash = 'password_hash' in existing_columns
                
                logging.info(f"Existing users table columns: {existing_columns}")
                logging.info(f"Has email column: {has_email}, Has password_hash column: {has_password_hash}")
                
                if existing_columns:
                    # Table exists, add missing columns
                    logging.info("Users table exists, checking for missing columns...")
                    
                    if not has_email:
                        logging.info("Adding email column...")
                        cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255);")
                        conn.commit()
                        logging.info("Email column added successfully")
                    
                    if not has_password_hash:
                        logging.info("Adding password_hash column...")
                        cursor.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);")
                        conn.commit()
                        logging.info("Password_hash column added successfully")
                    
                    # Add email index if it doesn't exist
                    cursor.execute("""
                        SELECT 1 FROM pg_indexes 
                        WHERE tablename = 'users' AND indexname = 'idx_users_email'
                    """)
                    if not cursor.fetchone():
                        logging.info("Creating email index...")
                        cursor.execute("CREATE INDEX idx_users_email ON users(email);")
                        conn.commit()
                        logging.info("Email index created successfully")
                    
                else:
                    # Table doesn't exist, create it with all columns
                    logging.info("Creating new users table...")
                    create_users_table = """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id VARCHAR(36) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        email VARCHAR(255),
                        password_hash VARCHAR(255),
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
                    cursor.execute(create_users_table)
                    conn.commit()
                    logging.info("Users table created successfully")
                
                # Create other indexes if they don't exist
                indexes_to_create = [
                    ("idx_users_email", "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);"),
                    ("idx_users_number", "CREATE INDEX IF NOT EXISTS idx_users_number ON users(number);"),
                    ("idx_users_stripe_customer", "CREATE INDEX IF NOT EXISTS idx_users_stripe_customer ON users(stripe_customer_id);"),
                    ("idx_users_active", "CREATE INDEX IF NOT EXISTS idx_users_active ON users(active);"),
                    ("idx_users_created_at", "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);")
                ]
                
                for index_name, index_sql in indexes_to_create:
                    try:
                        cursor.execute(index_sql)
                        conn.commit()
                        logging.info(f"Index {index_name} created/verified")
                    except Exception as e:
                        logging.warning(f"Could not create index {index_name}: {e}")
                        conn.rollback()
                
                # Message cache table (optional - for duplicate detection)
                create_message_cache_table = """
                CREATE TABLE IF NOT EXISTS message_cache (
                    id SERIAL PRIMARY KEY,
                    message_hash VARCHAR(64) UNIQUE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """
                cursor.execute(create_message_cache_table)
                conn.commit()
                logging.info("Message cache table created/verified")
                
                # Auto-cleanup old cache entries function
                create_cleanup_function = """
                CREATE OR REPLACE FUNCTION cleanup_old_messages()
                RETURNS void AS $$
                BEGIN
                    DELETE FROM message_cache 
                    WHERE created_at < NOW() - INTERVAL '24 hours';
                END;
                $$ LANGUAGE plpgsql;
                """
                cursor.execute(create_cleanup_function)
                conn.commit()
                logging.info("Cleanup function created/updated")
                
                logging.info("Database schema created/updated successfully")
                
    except Exception as e:
        logging.error(f"Error creating database schema: {e}")
        raise

def initialize_database():
    """Initialize database with schema and test connection"""
    try:
        # Test connection first
        if not db_config.test_connection():
            raise Exception("Database connection test failed")
        
        # Create/update schema
        create_tables()
        
        logging.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        return False
