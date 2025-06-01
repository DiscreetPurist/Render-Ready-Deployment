import os
import base64
from functools import wraps
from flask import request, jsonify

def check_auth(username, password):
    """Check if a username/password combination is valid"""
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    admin_password = os.getenv('ADMIN_PASSWORD', 'password123')
    
    return username == admin_username and password == admin_password

def authenticate():
    """Send a 401 response that enables basic auth"""
    return jsonify({
        'status': 'error',
        'message': 'Authentication required',
        'error': 'Please provide valid credentials'
    }), 401, {'WWW-Authenticate': 'Basic realm="Admin Area"'}

def requires_auth(f):
    """Decorator that requires authentication for a route"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        
        return f(*args, **kwargs)
    
    return decorated

def requires_auth_header(f):
    """Alternative decorator using Authorization header"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return authenticate()
        
        try:
            # Parse "Basic base64encodedcredentials"
            auth_type, credentials = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                return authenticate()
            
            # Decode base64 credentials
            decoded = base64.b64decode(credentials).decode('utf-8')
            username, password = decoded.split(':', 1)
            
            if not check_auth(username, password):
                return authenticate()
                
        except (ValueError, UnicodeDecodeError):
            return authenticate()
        
        return f(*args, **kwargs)
    
    return decorated

