import uuid
from datetime import datetime

class User:
    """User class for storing user information"""
    
    def __init__(self, name, number, location, range_miles, 
                 stripe_customer_id=None, subscription_id=None, 
                 created_at=None, updated_at=None, user_id=None):
        """
        Initialize a user with their details
        
        Args:
            name (str): User's name
            number (str): WhatsApp number
            location (str): Location like "Manchester m80gw"
            range_miles (int): Range in miles
            stripe_customer_id (str, optional): Stripe customer ID
            subscription_id (str, optional): Stripe subscription ID
            created_at (str, optional): Creation timestamp
            updated_at (str, optional): Last update timestamp
            user_id (str, optional): Unique user ID
        """
        self.name = name
        self.number = number
        self.location = location
        self.range_miles = range_miles
        self.stripe_customer_id = stripe_customer_id
        self.subscription_id = subscription_id
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or self.created_at
        self.user_id = user_id or str(uuid.uuid4())
        self.active = True
    
    def __str__(self):
        """String representation of user for logging purposes"""
        return f"{self.name} ({self.number}) - {self.location} ({self.range_miles} miles)"
    
    def to_dict(self):
        """
        Convert user object to dictionary for JSON serialization
        
        Returns:
            dict: User data as dictionary
        """
        return {
            'user_id': self.user_id,
            'name': self.name,
            'number': self.number,
            'location': self.location,
            'range_miles': self.range_miles,
            'stripe_customer_id': self.stripe_customer_id,
            'subscription_id': self.subscription_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'active': self.active
        }
    
    def update(self, **kwargs):
        """
        Update user attributes
        
        Args:
            **kwargs: Attributes to update
            
        Returns:
            User: Self for chaining
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.updated_at = datetime.utcnow().isoformat()
        return self
    
    @classmethod
    def from_dict(cls, data):
        """
        Create a User object from dictionary data
        
        Args:
            data (dict): Dictionary containing user data
            
        Returns:
            User: New User object
        """
        return cls(
            name=data.get('name'),
            number=data.get('number'),
            location=data.get('location'),
            range_miles=data.get('range_miles'),
            stripe_customer_id=data.get('stripe_customer_id'),
            subscription_id=data.get('subscription_id'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            user_id=data.get('user_id')
        )
