import uuid
from datetime import datetime

class User:
    """User model for the Recovery Manager application"""
    
    def __init__(self, name, number, location, range_miles, 
                 stripe_customer_id=None, subscription_id=None, 
                 user_id=None, active=True, created_at=None, updated_at=None):
        self.user_id = user_id or str(uuid.uuid4())
        self.name = name
        self.number = number
        self.location = location
        self.range_miles = range_miles
        self.stripe_customer_id = stripe_customer_id
        self.subscription_id = subscription_id
        self.active = active
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'number': self.number,
            'location': self.location,
            'range_miles': self.range_miles,
            'stripe_customer_id': self.stripe_customer_id,
            'subscription_id': self.subscription_id,
            'active': self.active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create user object from dictionary"""
        return cls(
            user_id=data.get('user_id'),
            name=data.get('name'),
            number=data.get('number'),
            location=data.get('location'),
            range_miles=data.get('range_miles'),
            stripe_customer_id=data.get('stripe_customer_id'),
            subscription_id=data.get('subscription_id'),
            active=data.get('active', True),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def __str__(self):
        return f"User({self.name}, {self.number}, {self.location})"
    
    def __repr__(self):
        return self.__str__()

