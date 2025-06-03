import uuid
from datetime import datetime

# Handle bcrypt import gracefully
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("Warning: bcrypt not available. Password hashing will be disabled.")

class User:
    """User model for the Recovery Manager application"""
    
    def __init__(self, name, email, number, location, range_miles, 
                 password_hash=None, stripe_customer_id=None, subscription_id=None, 
                 user_id=None, active=True, created_at=None, updated_at=None):
        self.user_id = user_id or str(uuid.uuid4())
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.number = number
        self.location = location
        self.range_miles = range_miles
        self.stripe_customer_id = stripe_customer_id
        self.subscription_id = subscription_id
        self.active = active
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()
    
    def set_password(self, password):
        """Hash and set password"""
        if not BCRYPT_AVAILABLE:
            raise RuntimeError("bcrypt is not available for password hashing")
        
        if password:
            salt = bcrypt.gensalt()
            self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches stored hash"""
        if not BCRYPT_AVAILABLE:
            return False
            
        if not self.password_hash or not password:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self, include_sensitive=False):
        """Convert user object to dictionary"""
        data = {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'number': self.number,
            'location': self.location,
            'range_miles': self.range_miles,
            'stripe_customer_id': self.stripe_customer_id,
            'subscription_id': self.subscription_id,
            'active': self.active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
        # Only include password hash for admin/internal use
        if include_sensitive:
            data['password_hash'] = self.password_hash
            
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create user object from dictionary"""
        return cls(
            user_id=data.get('user_id'),
            name=data.get('name'),
            email=data.get('email'),
            password_hash=data.get('password_hash'),
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
        return f"User({self.name}, {self.email}, {self.location})"
    
    def __repr__(self):
        return self.__str__()
