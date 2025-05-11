import json
import os
import logging
from datetime import datetime
from models.user import User

class UserManager:
    """User manager class to handle user operations"""
    
    def __init__(self, storage_file='users.json'):
        """
        Initialize UserManager with storage file path
        
        Args:
            storage_file (str): Path to JSON file for user data storage
        """
        self.users = []  # List to store User objects
        self.storage_file = storage_file  # File to store user data
        
        # Ensure directory exists for storage file
        storage_dir = os.path.dirname(self.storage_file)
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)
            
        self.load_users()  # Load users from storage on initialization
    
    def load_users(self):
        """
        Load users from JSON storage file into memory
        Handles file not found by starting with empty user list
        """
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    user_data = json.load(f)
                    # Convert each dictionary to User object
                    self.users = [User.from_dict(data) for data in user_data]
                logging.info(f"Loaded {len(self.users)} users from storage")
            else:
                logging.info("No user storage file found, starting with empty user list")
                # Create empty file
                self.save_users()
        except Exception as e:
            logging.error(f"Error loading users: {e}")
            # Create empty file on error
            self.save_users()
    
    def save_users(self):
        """
        Save all users from memory to JSON storage file
        Converts User objects to dictionaries before serialization
        """
        try:
            with open(self.storage_file, 'w') as f:
                # Convert User objects to dictionaries for JSON serialization
                json.dump([user.to_dict() for user in self.users], f)
            logging.info(f"Saved {len(self.users)} users to storage")
            return True
        except Exception as e:
            logging.error(f"Error saving users: {e}")
            return False
    
    def add_user(self, name, number, location, range_miles, stripe_customer_id=None, subscription_id=None):
        """
        Add a new user to the system
        
        Args:
            name (str): User's name
            number (str): WhatsApp number
            location (str): Location (city/postcode)
            range_miles (int): Range in miles
            stripe_customer_id (str, optional): Stripe customer ID
            subscription_id (str, optional): Stripe subscription ID
            
        Returns:
            User: The newly created user
        """
        # Check if user already exists
        existing_user = self.get_user_by_number(number)
        if existing_user:
            # Update existing user
            existing_user.update(
                name=name,
                location=location,
                range_miles=range_miles,
                stripe_customer_id=stripe_customer_id or existing_user.stripe_customer_id,
                subscription_id=subscription_id or existing_user.subscription_id,
                active=True
            )
            self.save_users()
            return existing_user
            
        # Create new user
        user = User(
            name=name, 
            number=number, 
            location=location, 
            range_miles=range_miles,
            stripe_customer_id=stripe_customer_id,
            subscription_id=subscription_id
        )
        self.users.append(user)
        self.save_users()  # Persist changes to storage
        return user
    
    def get_users(self, active_only=True):
        """
        Get all users in the system
        
        Args:
            active_only (bool): Whether to return only active users
            
        Returns:
            list: List of User objects
        """
        if active_only:
            return [user for user in self.users if getattr(user, 'active', True)]
        return self.users
    
    def get_user_by_number(self, number):
        """
        Find a user by their WhatsApp number
        
        Args:
            number (str): WhatsApp number to search for
            
        Returns:
            User: User object if found, None otherwise
        """
        for user in self.users:
            if user.number == number:
                return user
        return None
    
    def get_user_by_id(self, user_id):
        """
        Find a user by their ID
        
        Args:
            user_id (str): User ID to search for
            
        Returns:
            User: User object if found, None otherwise
        """
        for user in self.users:
            if user.user_id == user_id:
                return user
        return None
    
    def get_user_by_stripe_customer_id(self, stripe_customer_id):
        """
        Find a user by their Stripe customer ID
        
        Args:
            stripe_customer_id (str): Stripe customer ID to search for
            
        Returns:
            User: User object if found, None otherwise
        """
        for user in self.users:
            if user.stripe_customer_id == stripe_customer_id:
                return user
        return None
    
    def update_user(self, number, **kwargs):
        """
        Update user attributes
        
        Args:
            number (str): WhatsApp number of user to update
            **kwargs: Attributes to update (name, location, range_miles)
            
        Returns:
            User: Updated user object if found, None otherwise
        """
        user = self.get_user_by_number(number)
        if user:
            # Update user
            user.update(**kwargs)
            self.save_users()  # Persist changes
            return user
        return None
    
    def deactivate_user(self, number):
        """
        Deactivate a user (soft delete)
        
        Args:
            number (str): WhatsApp number of user to deactivate
            
        Returns:
            bool: True if user was deactivated, False if not found
        """
        user = self.get_user_by_number(number)
        if user:
            user.update(active=False)
            self.save_users()
            return True
        return False
    
    def delete_user(self, number):
        """
        Delete a user by number (hard delete)
        
        Args:
            number (str): WhatsApp number of user to delete
            
        Returns:
            bool: True if user was deleted, False if not found
        """
        user = self.get_user_by_number(number)
        if user:
            self.users.remove(user)
            self.save_users()  # Persist changes
            return True
        return False
