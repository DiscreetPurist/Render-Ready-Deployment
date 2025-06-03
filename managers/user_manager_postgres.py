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
    
    def add_user(self, name, email, number, location, range_miles, 
                 password=None, stripe_customer_id=None, subscription_id=None):
        """
        Add a new user to the database
        
        Args:
            name (str): User's name
            email (str): User's email
            number (str): WhatsApp number
            location (str): User's location
            range_miles (int): Range in miles
            password (str, optional): Plain text password (will be hashed)
            stripe_customer_id (str, optional): Stripe customer ID
            subscription_id (str, optional): Stripe subscription ID
            
        Returns:
            User: The created or updated user
        """
        try:
            # Check if user already exists by email or number
            existing_user = None
            if email:
                existing_user = self.get_user_by_email(email)
            if not existing_user:
                existing_user = self.get_user_by_number(number)
            
            if existing_user:
                # Update existing user
                update_data = {
                    'name': name,
                    'location': location,
                    'range_miles': range_miles,
                    'active': True
                }
                
                # Update email if provided and different
                if email and email != existing_user.email:
                    update_data['email'] = email
                
                if stripe_customer_id:
                    update_data['stripe_customer_id'] = stripe_customer_id
                if subscription_id:
                    update_data['subscription_id'] = subscription_id
                if password:
                    # Update password
                    existing_user.set_password(password)
                    update_data['password_hash'] = existing_user.password_hash
                
                # Use email if available, otherwise use number for update
                if existing_user.email:
                    return self.update_user_by_email(existing_user.email, **update_data)
                else:
                    return self.update_user(existing_user.number, **update_data)
            
            # Create new user
            user_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            # Create user object to hash password
            user = User(
                user_id=user_id,
                name=name,
                email=email or f"user_{user_id}@temp.local",  # Temporary email if none provided
                number=number,
                location=location,
                range_miles=range_miles,
                stripe_customer_id=stripe_customer_id,
                subscription_id=subscription_id,
                active=True,
                created_at=now,
                updated_at=now
            )
            
            if password:
                user.set_password(password)
            
            with self.db_config.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO users (
                            user_id, name, email, password_hash, number, location, range_miles, 
                            stripe_customer_id, subscription_id, active, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *;
                    """, (
                        user.user_id, user.name, user.email, user.password_hash, user.number, 
                        user.location, user.range_miles, user.stripe_customer_id, 
                        user.subscription_id, user.active, user.created_at, user.updated_at
                    ))
                    
                    row = cursor.fetchone()
                    conn.commit()
                    
                    # Convert to User object
                    user_data = {
                        'user_id': row[0],
                        'name': row[1],
                        'email': row[2],
                        'password_hash': row[3],
                        'number': row[4],
                        'location': row[5],
                        'range_miles': row[6],
                        'stripe_customer_id': row[7],
                        'subscription_id': row[8],
                        'active': row[9],
                        'created_at': row[10].isoformat() if row[10] else now,
                        'updated_at': row[11].isoformat() if row[11] else now
                    }
                    
                    created_user = User.from_dict(user_data)
                    logging.info(f"Added user: {created_user.name} ({created_user.email})")
                    return created_user
                    
        except Exception as e:
            logging.error(f"Error adding user: {e}")
            raise
    
    def get_user_by_email(self, email):
        """
        Get user by email address
        
        Args:
            email (str): Email address
            
        Returns:
            User: User object if found, None otherwise
        """
        if not email:
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
                            user_data['created_at'] = user_data['created_at'].isoformat()
                        if user_data.get('updated_at'):
                            user_data['updated_at'] = user_data['updated_at'].isoformat()
                        
                        return User.from_dict(user_data)
                    
                    return None
                    
        except Exception as e:
            logging.error(f"Error getting user by email: {e}")
            return None
    
    def authenticate_user(self, email, password):
        """
        Authenticate user with email and password
        
        Args:
            email (str): Email address
            password (str): Plain text password
            
        Returns:
            User: User object if authentication successful, None otherwise
        """
        try:
            user = self.get_user_by_email(email)
            if user and user.check_password(password):
                return user
            return None
        except Exception as e:
            logging.error(f"Error authenticating user: {e}")
            return None
    
    def update_user_by_email(self, email, **kwargs):
        """
        Update user by email address
        
        Args:
            email (str): Email address of user to update
            **kwargs: Fields to update
            
        Returns:
            User: Updated user object if found, None otherwise
        """
        if not email:
            return None
            
        try:
            # Build dynamic update query
            set_clauses = []
            values = []
            
            # Valid fields that can be updated
            valid_fields = ['name', 'email', 'location', 'range_miles', 'stripe_customer_id', 
                          'subscription_id', 'active', 'password_hash']
            
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
        """
        Get all users from database
        
        Args:
            active_only (bool): Whether to return only active users
            
        Returns:
            list: List of User objects
        """
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
                            user_data['created_at'] = user_data['created_at'].isoformat()
                        if user_data.get('updated_at'):
                            user_data['updated_at'] = user_data['updated_at'].isoformat()
                        
                        users.append(User.from_dict(user_data))
                    
                    return users
                    
        except Exception as e:
            logging.error(f"Error getting users: {e}")
            return []
    
    def get_user_by_number(self, number):
        """
        Get user by phone number
        
        Args:
            number (str): WhatsApp number
            
        Returns:
            User: User object if found, None otherwise
        """
        try:
            with self.db_config.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT * FROM users WHERE number = %s", (number,))
                    row = cursor.fetchone()
                    
                    if row:
                        user_data = dict(row)
                        # Convert timestamps to ISO format
                        if user_data.get('created_at'):
                            user_data['created_at'] = user_data['created_at'].isoformat()
                        if user_data.get('updated_at'):
                            user_data['updated_at'] = user_data['updated_at'].isoformat()
                        
                        return User.from_dict(user_data)
                    
                    return None
                    
        except Exception as e:
            logging.error(f"Error getting user by number: {e}")
            return None
    
    def get_user_by_stripe_customer_id(self, stripe_customer_id):
        """
        Get user by Stripe customer ID
        
        Args:
            stripe_customer_id (str): Stripe customer ID
            
        Returns:
            User: User object if found, None otherwise
        """
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
                            user_data['created_at'] = user_data['created_at'].isoformat()
                        if user_data.get('updated_at'):
                            user_data['updated_at'] = user_data['updated_at'].isoformat()
                        
                        return User.from_dict(user_data)
                    
                    return None
                    
        except Exception as e:
            logging.error(f"Error getting user by Stripe ID: {e}")
            return None
    
    def update_user(self, number, **kwargs):
        """
        Update user in database by phone number
        
        Args:
            number (str): WhatsApp number of user to update
            **kwargs: Fields to update
            
        Returns:
            User: Updated user object if found, None otherwise
        """
        try:
            # Build dynamic update query
            set_clauses = []
            values = []
            
            # Valid fields that can be updated
            valid_fields = ['name', 'email', 'location', 'range_miles', 'stripe_customer_id', 
                          'subscription_id', 'active', 'password_hash']
            
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
        """
        Deactivate user (soft delete)
        
        Args:
            number (str): WhatsApp number
            
        Returns:
            bool: True if successful, False otherwise
        """
        result = self.update_user(number, active=False)
        return result is not None
    
    def delete_user(self, number):
        """
        Hard delete user from database
        
        Args:
            number (str): WhatsApp number
            
        Returns:
            bool: True if successful, False otherwise
        """
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


