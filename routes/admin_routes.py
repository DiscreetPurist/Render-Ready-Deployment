from flask import Blueprint, jsonify, request
import logging
from datetime import datetime
from utils.auth import requires_auth

# Create a Blueprint for admin routes
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/login', methods=['POST'])
def admin_login():
    """Test login endpoint"""
    try:
        auth = request.authorization
        
        if not auth:
            return jsonify({
                'status': 'error',
                'message': 'No credentials provided'
            }), 401
        
        from utils.auth import check_auth
        
        if check_auth(auth.username, auth.password):
            return jsonify({
                'status': 'success',
                'message': 'Authentication successful',
                'user': auth.username
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Invalid credentials'
            }), 401
            
    except Exception as e:
        logging.error(f"Login error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Login failed'
        }), 500

@admin_bp.route('/admin/database/stats', methods=['GET'])
@requires_auth
def database_stats():
    """Get database statistics - PROTECTED"""
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        # Get basic stats
        all_users = user_manager.get_users(active_only=False)
        active_users = user_manager.get_users(active_only=True)
        
        # Calculate stats
        total_users = len(all_users)
        active_count = len(active_users)
        inactive_count = total_users - active_count
        
        # Get recent signups (last 7 days)
        recent_signups = []
        for user in all_users:
            try:
                created_date = datetime.fromisoformat(user.created_at.replace('Z', '+00:00'))
                days_ago = (datetime.now(created_date.tzinfo) - created_date).days
                if days_ago <= 7:
                    recent_signups.append(user)
            except Exception as e:
                logging.debug(f"Error parsing date: {e}")
                continue
        
        return jsonify({
            'status': 'success',
            'stats': {
                'total_users': total_users,
                'active_users': active_count,
                'inactive_users': inactive_count,
                'recent_signups_7_days': len(recent_signups)
            },
            'recent_users': [
                {
                    'name': user.name,
                    'number': user.number,
                    'location': user.location,
                    'range_miles': user.range_miles,
                    'created_at': user.created_at,
                    'active': getattr(user, 'active', True),
                    'stripe_customer_id': user.stripe_customer_id,
                    'subscription_id': user.subscription_id
                } for user in sorted(all_users, key=lambda x: x.created_at, reverse=True)[:5]
            ]
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting database stats: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_bp.route('/admin/database/users', methods=['GET'])
@requires_auth
def list_users():
    """List all users with pagination - PROTECTED"""
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        # Get query parameters
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 users
        offset = int(request.args.get('offset', 0))
        
        users = user_manager.get_users(active_only=active_only)
        
        # Sort by created_at (newest first)
        users = sorted(users, key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        paginated_users = users[offset:offset + limit]
        
        return jsonify({
            'status': 'success',
            'total_count': len(users),
            'returned_count': len(paginated_users),
            'offset': offset,
            'limit': limit,
            'users': [user.to_dict() for user in paginated_users]
        }), 200
        
    except Exception as e:
        logging.error(f"Error listing users: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_bp.route('/admin/database/users/<number>', methods=['GET'])
@requires_auth
def get_user_details(number):
    """Get detailed information about a specific user - PROTECTED"""
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        user = user_manager.get_user_by_number(number)
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Get user details
        user_data = user.to_dict()
        
        return jsonify({
            'status': 'success',
            'user': user_data
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting user details: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_bp.route('/admin/database/users/<number>', methods=['PUT'])
@requires_auth
def update_user_admin(number):
    """Update user details - PROTECTED"""
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        # Update user
        user = user_manager.update_user(number, **data)
        if user:
            return jsonify({
                'status': 'success',
                'message': 'User updated successfully',
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
    except Exception as e:
        logging.error(f"Error updating user: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_bp.route('/admin/database/users/<number>', methods=['DELETE'])
@requires_auth
def delete_user_admin(number):
    """Delete user - PROTECTED"""
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        soft_delete = request.args.get('soft', 'true').lower() == 'true'
        
        if soft_delete:
            success = user_manager.deactivate_user(number)
            message = 'User deactivated successfully'
        else:
            success = user_manager.delete_user(number)
            message = 'User deleted successfully'
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message
            }), 200
        else:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
    except Exception as e:
        logging.error(f"Error deleting user: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_bp.route('/admin/export/users', methods=['GET'])
@requires_auth
def export_users():
    """Export users as CSV - PROTECTED"""
    try:
        from app import user_manager
        import csv
        import io
        from flask import make_response
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        # Get all users
        users = user_manager.get_users(active_only=False)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Name', 'Number', 'Location', 'Range (Miles)', 
            'Active', 'Created At', 'Stripe Customer ID', 'Subscription ID'
        ])
        
        # Write user data
        for user in users:
            writer.writerow([
                user.name,
                user.number,
                user.location,
                user.range_miles,
                getattr(user, 'active', True),
                user.created_at,
                user.stripe_customer_id or '',
                user.subscription_id or ''
            ])
        
        # Create response
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=users_export.csv'
        
        return response
        
    except Exception as e:
        logging.error(f"Error exporting users: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
