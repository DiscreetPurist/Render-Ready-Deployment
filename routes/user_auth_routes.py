from flask import Blueprint, request, jsonify, session
import logging
from functools import wraps

# Create a Blueprint for user authentication
user_auth_bp = Blueprint('user_auth', __name__)

def require_user_auth(f):
    """Decorator to require user authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@user_auth_bp.route('/api/user/login', methods=['POST'])
def user_login():
    """User login endpoint"""
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'status': 'error', 'message': 'Email and password required'}), 400
        
        # Authenticate user
        user = user_manager.authenticate_user(email, password)
        if user:
            # Store user session
            session['user_email'] = user.email
            session['user_id'] = user.user_id
            
            logging.info(f"User login successful: {user.email}")
            
            return jsonify({
                'status': 'success',
                'message': 'Login successful',
                'user': user.to_dict()
            }), 200
        else:
            logging.warning(f"Failed login attempt: {email}")
            return jsonify({'status': 'error', 'message': 'Invalid email or password'}), 401
            
    except Exception as e:
        logging.error(f"User login error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@user_auth_bp.route('/api/user/logout', methods=['POST'])
def user_logout():
    """User logout endpoint"""
    if 'user_email' in session:
        email = session['user_email']
        session.pop('user_email', None)
        session.pop('user_id', None)
        logging.info(f"User logout: {email}")
    
    return jsonify({'status': 'success', 'message': 'Logged out successfully'}), 200

@user_auth_bp.route('/api/user/verify-session', methods=['GET'])
def verify_user_session():
    """Verify if user session is valid"""
    try:
        from app import user_manager
        
        if 'user_email' not in session:
            return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
        
        # Get current user data
        user = user_manager.get_user_by_email(session['user_email'])
        if not user or not user.active:
            # Clear invalid session
            session.pop('user_email', None)
            session.pop('user_id', None)
            return jsonify({'status': 'error', 'message': 'Account not found or inactive'}), 401
        
        return jsonify({
            'status': 'success',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logging.error(f"Session verification error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@user_auth_bp.route('/api/user/profile', methods=['GET'])
@require_user_auth
def get_user_profile():
    """Get current user profile"""
    try:
        from app import user_manager
        
        user = user_manager.get_user_by_email(session['user_email'])
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        return jsonify({
            'status': 'success',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logging.error(f"Get profile error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@user_auth_bp.route('/api/user/profile', methods=['PUT'])
@require_user_auth
def update_user_profile():
    """Update user profile"""
    try:
        from app import user_manager
        
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        # Get current user
        user = user_manager.get_user_by_email(session['user_email'])
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Validate range if provided
        if 'range_miles' in data:
            try:
                range_miles = int(data['range_miles'])
                if range_miles < 1 or range_miles > 200:
                    return jsonify({'status': 'error', 'message': 'Range must be between 1 and 200 miles'}), 400
                data['range_miles'] = range_miles
            except (ValueError, TypeError):
                return jsonify({'status': 'error', 'message': 'Range must be a valid number'}), 400
        
        # Update user
        updated_user = user_manager.update_user_by_email(session['user_email'], **data)
        if updated_user:
            logging.info(f"User profile updated: {session['user_email']}")
            return jsonify({
                'status': 'success',
                'message': 'Profile updated successfully',
                'user': updated_user.to_dict()
            }), 200
        else:
            return jsonify({'status': 'error', 'message': 'Update failed'}), 400
            
    except Exception as e:
        logging.error(f"Update profile error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@user_auth_bp.route('/api/user/change-password', methods=['POST'])
@require_user_auth
def change_password():
    """Change user password"""
    try:
        from app import user_manager
        
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'status': 'error', 'message': 'Current and new password required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'status': 'error', 'message': 'New password must be at least 6 characters'}), 400
        
        # Get current user
        user = user_manager.get_user_by_email(session['user_email'])
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Verify current password
        if not user.check_password(current_password):
            return jsonify({'status': 'error', 'message': 'Current password is incorrect'}), 401
        
        # Update password
        user.set_password(new_password)
        updated_user = user_manager.update_user_by_email(session['user_email'], password_hash=user.password_hash)
        
        if updated_user:
            logging.info(f"Password changed for user: {session['user_email']}")
            return jsonify({
                'status': 'success',
                'message': 'Password changed successfully'
            }), 200
        else:
            return jsonify({'status': 'error', 'message': 'Password change failed'}), 400
            
    except Exception as e:
        logging.error(f"Change password error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@user_auth_bp.route('/api/user/deactivate-account', methods=['POST'])
@require_user_auth
def deactivate_account():
    """Deactivate user account and cancel subscription"""
    try:
        from app import user_manager
        import stripe
        import os
        
        data = request.json
        password = data.get('password') if data else None
        
        if not password:
            return jsonify({'status': 'error', 'message': 'Password required to deactivate account'}), 400
        
        # Get current user
        user = user_manager.get_user_by_email(session['user_email'])
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Verify password
        if not user.check_password(password):
            return jsonify({'status': 'error', 'message': 'Incorrect password'}), 401
        
        # Cancel Stripe subscription if exists
        if user.subscription_id:
            try:
                stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
                stripe.Subscription.delete(user.subscription_id)
                logging.info(f"Cancelled subscription {user.subscription_id} for user {user.email}")
            except Exception as e:
                logging.error(f"Error cancelling subscription: {e}")
                # Continue with account deactivation even if Stripe fails
        
        # Deactivate user account
        success = user_manager.update_user_by_email(session['user_email'], active=False)
        
        if success:
            # Clear session
            session.pop('user_email', None)
            session.pop('user_id', None)
            
            logging.info(f"Account deactivated: {user.email}")
            return jsonify({
                'status': 'success',
                'message': 'Account deactivated successfully'
            }), 200
        else:
            return jsonify({'status': 'error', 'message': 'Account deactivation failed'}), 400
            
    except Exception as e:
        logging.error(f"Account deactivation error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
