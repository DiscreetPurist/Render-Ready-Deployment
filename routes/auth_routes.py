from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
import os
import logging
from functools import wraps

# Create a Blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

# Admin credentials (in production, use environment variables and hashed passwords)
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')  # Change this!

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user' not in session:
            # API requests
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
            # Browser requests
            return redirect('/admin/login')
        
        return f(*args, **kwargs)
    
    return decorated_function

@auth_bp.route('/admin/login', methods=['GET'])
def admin_login_page():
    """Admin login page"""
    # If already logged in, redirect to admin dashboard
    if 'admin_user' in session:
        return redirect('/admin')
    return render_template('admin_login.html')

@auth_bp.route('/admin/login', methods=['POST'])
def admin_login():
    """Handle admin login"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'status': 'error', 'message': 'Username and password required'}), 400
        
        # Check credentials
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            # Store in session
            session['admin_user'] = username
            logging.info(f"Admin login successful: {username}")
            
            return jsonify({
                'status': 'success',
                'message': 'Login successful',
                'username': username
            }), 200
        else:
            logging.warning(f"Failed login attempt: {username}")
            return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401
            
    except Exception as e:
        logging.error(f"Login error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@auth_bp.route('/admin/verify-session', methods=['GET'])
def verify_admin_session():
    """Verify if admin session is valid"""
    if 'admin_user' in session:
        return jsonify({
            'status': 'success',
            'username': session['admin_user']
        }), 200
    else:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401

@auth_bp.route('/admin/logout', methods=['POST'])
def admin_logout():
    """Handle admin logout"""
    if 'admin_user' in session:
        username = session['admin_user']
        session.pop('admin_user', None)
        logging.info(f"Admin logout: {username}")
    
    return jsonify({'status': 'success', 'message': 'Logged out successfully'}), 200
