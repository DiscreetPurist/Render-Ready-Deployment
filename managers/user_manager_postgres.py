import logging
import uuid
from datetime import datetime
from psycopg2.extras import RealDictCursor
from models.user import User
from config.database import db_config

class UserManager:
    """PostgreSQL-backed user manager for production"""
    
    def __init__(self):
        """Initialize user manager"""
        self.db_config = db_config
        self._check_table_structure()
    
    def _check_table_structure(self):
        """Check if the users table has the required columns"""
        try:
            with self.db_config.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'users'
                    """)
                    columns = [row[0] for row in cursor.fetchall()]
                    
                    self.has_email = 'email' in columns
                    self.has_password_hash = 'password_hash' in columns
                    
                    logging.info(f"UserManager initialized - Email column: {self.has_email}, Password column: {self.has_password_hash}")
                    
        except Exception as e:
            logging.error(f"Error checking table structure: {e}")
            self.has_email = False
            self.has_password_hash = False
    
    def _format_timestamp(self, timestamp):
        """Format timestamp to ISO format string, handling both datetime objects and strings"""
        if timestamp is None:
            return None
        if isinstance(timestamp, str):
            return timestamp
        try:
            return timestamp.isoformat()
        except AttributeError:
            return str(timestamp)
    
    def add_user(self, name, email, number, location, range_miles, 
                 password=None, stripe_customer_id=None, subscription_id=None):
        """
        Add a new user to the database
        """
        try:
            # Check if user already exists by number (always available)
            existing_user = self.get_user_by_number(number)
            
            # Also check by email if email column exists and email is provided
            if not existing_user and self.has_email and email:
                existing_user = self.get_user_by_email(email)
            
            if existing_user:
                # Update existing user
                update_data = {
                    'name': name,
                    'location': location,
                    'range_miles': range_miles,
                    'active': True
                }
                
                # Update email if column exists and email provided
                if self.has_email and email and email != getattr(existing_user, 'email', None):
                    update_data['email'] = email
                
                if stripe_customer_id:
                    update_data['stripe_customer_id'] = stripe_customer_id
                if subscription_id:
                    update_data['subscription_id'] = subscription_id
                if password and self.has_password_hash:
                    # Update password
                    existing_user.set_password(password)
                    update_data['password_hash'] = existing_user.password_hash
                
                return self.update_user(existing_user.number, **update_data)
            
            # Create new user
            user_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            # Build insert query based on available columns
            columns = ['user_id', 'name', 'number', 'location', 'range_miles', 'active', 'created_at', 'updated_at']
            values = [user_id, name, number, location, range_miles, True, now, now]
            placeholders = ['%s'] * len(values)
            
            # Add email if column exists
            if self.has_email:
                columns.append('email')
                values.append(email or f"user_{user_id}@temp.local")
                placeholders.append('%s')
            
            # Add password if column exists and password provided
            if self.has_password_hash:
                user = User(
                    user_id=user_id,
                    name=name,
                    email=email or f"user_{user_id}@temp.local",
                    number=number,
                    location=location,
                    range_miles=range_miles,
                    active=True,
                    created_at=now,
                    updated_at=now
                )
                
                if password:
                    user.set_password(password)
                
                columns.append('password_hash')
                values.append(user.password_hash)
                placeholders.append('%s')
            
            # Add Stripe fields if provided
            if stripe_customer_id:
                columns.append('stripe_customer_id')
                values.append(stripe_customer_id)
                placeholders.append('%s')
            
            if subscription_id:
                columns.append('subscription_id')
                values.append(subscription_id)
                placeholders.append('%s')
            
            with self.db_config.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = f"""
                        INSERT INTO users ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                        RETURNING *;
                    """
                    cursor.execute(query, values)
                    
                    row = cursor.fetchone()
                    conn.commit()
                    
                    # Convert to User object
                    user_data = {
                        'user_id': row[0],
                        'name': row[1],
                        'number': row[2] if not self.has_email else row[4],  # Adjust for email column
                        'location': row[3] if not self.has_email else row[5],
                        'range_miles': row[4] if not self.has_email else row[6],
                        'active': row[7] if not self.has_email else row[9],
                        'created_at': self._format_timestamp(row[8] if not self.has_email else row[10]) or now,
                        'updated_at': self._format_timestamp(row[9] if not self.has_email else row[11]) or now
                    }
                    
                    # Add email and password_hash if columns exist
                    if self.has_email:
                        user_data['email'] = row[2]
                    else:
                        user_data['email'] = email or f"user_{user_id}@temp.local"
                    
                    if self.has_password_hash:
                        user_data['password_hash'] = row[3] if not self.has_email else row[7]
                    
                    # Add Stripe fields
                    stripe_customer_idx = len(row) - 2 if subscription_id else len(row) - 1 if stripe_customer_id else None
                    subscription_idx = len(row) - 1 if subscription_id else None
                    
                    user_data['stripe_customer_id'] = row[stripe_customer_idx] if stripe_customer_idx else stripe_customer_id
                    user_data['subscription_id'] = row[subscription_idx] if subscription_idx else subscription_id
                    
                    created_user = User.from_dict(user_data)
                    logging.info(f"Added user: {created_user.name} ({getattr(created_user, 'email', 'no-email')})")
                    return created_user
                    
        except Exception as e:
            logging.error(f"Error adding user: {e}")
            raise
    
    def get_user_by_email(self, email):
        """Get user by email address (only if email column exists)"""
        if not self.has_email or not email:
            return None
            
        try:
            with self.db_config.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                    row = cursor.fetchone()
                    
                    if row:
                        user_data = dict(row)
                        # Convert timestamps to ISO format
                        if user_data.get('created_at'):
                            user_data['created_at'] = self._format_timestamp(user_data['created_at'])
                        if user_data.get('updated_at'):
                            user_data['updated_at'] = self._format_timestamp(user_data['updated_at'])
                        
                        return User.from_dict(user_data)
                    
                    return None
                    
        except Exception as e:
            logging.error(f"Error getting user by email: {e}")
            return None
    
    def authenticate_user(self, email, password):
        """Authenticate user with email and password (only if both columns exist)"""
        if not self.has_email or not self.has_password_hash:
            logging.warning("Authentication not available - missing email or password columns")
            return None
            
        try:
            user = self.get_user_by_email(email)
            if user and user.check_password(password):
                return user
            return None
        except Exception as e:
            logging.error(f"Error authenticating user: {e}")
            return None
    
    def update_user_by_email(self, email, **kwargs):
        """Update user by email address (only if email column exists)"""
        if not self.has_email or not email:
            return None
            
        try:
            # Build dynamic update query
            set_clauses = []
            values = []
            
            # Valid fields that can be updated (check if columns exist)
            valid_fields = ['name', 'location', 'range_miles', 'stripe_customer_id', 'subscription_id', 'active']
            
            if self.has_email:
                valid_fields.append('email')
            if self.has_password_hash:
                valid_fields.append('password_hash')
            
            for key, value in kwargs.items():
                if key in valid_fields:
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
            
            if not set_clauses:
                return self.get_user_by_email(email)
            
            # Add updated_at
            set_clauses.append("updated_at = %s")
            values.append(datetime.utcnow())
            values.append(email)  # For WHERE clause
            
            with self.db_config.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = f"UPDATE users SET {', '.join(set_clauses)} WHERE email = %s"
                    cursor.execute(query, values)
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        return self.get_user_by_email(email)
            
            return None
            
        except Exception as e:
            logging.error(f"Error updating user by email: {e}")
            return None
    
    def get_users(self, active_only=True):
        """Get all users from database"""
        try:
            with self.db_config.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    if active_only:
                        cursor.execute("SELECT * FROM users WHERE active = TRUE ORDER BY created_at DESC")
                    else:
                        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
                    
                    rows = cursor.fetchall()
                    users = []
                    
                    for row in rows:
                        user_data = dict(row)
                        # Convert timestamps to ISO format
                        if user_data.get('created_at'):
                            user_data['created_at'] = self._format_timestamp(user_data['created_at'])
                        if user_data.get('updated_at'):
                            user_data['updated_at'] = self._format_timestamp(user_data['updated_at'])
                        
                        # Add default email if column doesn't exist
                        if not self.has_email:
                            user_data['email'] = f"user_{user_data.get('user_id', 'unknown')}@temp.local"
                        
                        # Add default password_hash if column doesn't exist
                        if not self.has_password_hash:
                            user_data['password_hash'] = None
                        
                        users.append(User.from_dict(user_data))
                    
                    return users
                    
        except Exception as e:
            logging.error(f"Error getting users: {e}")
            return []
    
    def get_user_by_number(self, number):
        """Get user by phone number"""
        try:
            with self.db_config.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT * FROM users WHERE number = %s", (number,))
                    row = cursor.fetchone()
                    
                    if row:
                        user_data = dict(row)
                        # Convert timestamps to ISO format
                        if user_data.get('created_at'):
                            user_data['created_at'] = self._format_timestamp(user_data['created_at'])
                        if user_data.get('updated_at'):
                            user_data['updated_at'] = self._format_timestamp(user_data['updated_at'])
                        
                        # Add default email if column doesn't exist
                        if not self.has_email:
                            user_data['email'] = f"user_{user_data.get('user_id', 'unknown')}@temp.local"
                        
                        # Add default password_hash if column doesn't exist
                        if not self.has_password_hash:
                            user_data['password_hash'] = None
                        
                        return User.from_dict(user_data)
                    
                    return None
                    
        except Exception as e:
            logging.error(f"Error getting user by number: {e}")
            return None
    
    def get_user_by_stripe_customer_id(self, stripe_customer_id):
        """Get user by Stripe customer ID"""
        try:
            with self.db_config.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT * FROM users WHERE stripe_customer_id = %s", 
                                 (stripe_customer_id,))
                    row = cursor.fetchone()
                    
                    if row:
                        user_data = dict(row)
                        # Convert timestamps to ISO format
                        if user_data.get('created_at'):
                            user_data['created_at'] = self._format_timestamp(user_data['created_at'])
                        if user_data.get('updated_at'):
                            user_data['updated_at'] = self._format_timestamp(user_data['updated_at'])
                        
                        # Add default email if column doesn't exist
                        if not self.has_email:
                            user_data['email'] = f"user_{user_data.get('user_id', 'unknown')}@temp.local"
                        
                        # Add default password_hash if column doesn't exist
                        if not self.has_password_hash:
                            user_data['password_hash'] = None
                        
                        return User.from_dict(user_data)
                    
                    return None
                    
        except Exception as e:
            logging.error(f"Error getting user by Stripe ID: {e}")
            return None
    
    def update_user(self, number, **kwargs):
        """Update user in database by phone number"""
        try:
            # Build dynamic update query
            set_clauses = []
            values = []
            
            # Valid fields that can be updated (check if columns exist)
            valid_fields = ['name', 'location', 'range_miles', 'stripe_customer_id', 'subscription_id', 'active']
            
            if self.has_email:
                valid_fields.append('email')
            if self.has_password_hash:
                valid_fields.append('password_hash')
            
            for key, value in kwargs.items():
                if key in valid_fields:
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
            
            if not set_clauses:
                return self.get_user_by_number(number)
            
            # Add updated_at
            set_clauses.append("updated_at = %s")
            values.append(datetime.utcnow())
            values.append(number)  # For WHERE clause
            
            with self.db_config.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = f"UPDATE users SET {', '.join(set_clauses)} WHERE number = %s"
                    cursor.execute(query, values)
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        return self.get_user_by_number(number)
            
            return None
            
        except Exception as e:
            logging.error(f"Error updating user: {e}")
            return None
    
    def deactivate_user(self, number):
        """Deactivate user (soft delete)"""
        result = self.update_user(number, active=False)
        return result is not None
    
    def delete_user(self, number):
        """Hard delete user from database"""
        try:
            with self.db_config.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM users WHERE number = %s", (number,))
                    conn.commit()
                    return cursor.rowcount > 0
                    
        except Exception as e:
            logging.error(f"Error deleting user: {e}")
            return False
    
    def get_user_count(self):
        """Get total number of users"""
        try:
            with self.db_config.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM users WHERE active = TRUE")
                    return cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"Error getting user count: {e}")
            return 0
