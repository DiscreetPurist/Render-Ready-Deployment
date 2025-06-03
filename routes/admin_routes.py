from flask import Blueprint, jsonify, request
import logging
from datetime import datetime

# Create a Blueprint for admin routes
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/database/stats', methods=['GET'])
def database_stats():
    """Get database statistics"""
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
                    'active': getattr(user, 'active', True)
                } for user in sorted(all_users, key=lambda x: x.created_at, reverse=True)[:5]
            ]
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting database stats: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_bp.route('/admin/database/users', methods=['GET'])
def list_users():
    """List all users with pagination"""
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
def get_user_details(number):
    """Get detailed information about a specific user"""
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
def admin_update_user(number):
    """Admin endpoint to update a user"""
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        # Get current user first
        current_user = user_manager.get_user_by_number(number)
        if not current_user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Update user with provided data
        updated_user = user_manager.update_user(number, **data)
        if updated_user:
            logging.info(f"Admin updated user {number}: {list(data.keys())}")
            return jsonify({
                'status': 'success',
                'message': 'User updated successfully',
                'user': updated_user.to_dict(),
                'changes': list(data.keys())
            }), 200
        else:
            return jsonify({'status': 'error', 'message': 'Update failed'}), 400
            
    except Exception as e:
        logging.error(f"Admin update user error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_bp.route('/admin/database/users/<number>', methods=['DELETE'])
def admin_delete_user(number):
    """Admin endpoint to delete a user (soft or hard delete)"""
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        # Check if user exists
        user = user_manager.get_user_by_number(number)
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Get delete type from query parameter (default to soft delete)
        delete_type = request.args.get('type', 'soft')
        
        if delete_type == 'hard':
            # Hard delete - permanently remove from database
            success = user_manager.delete_user(number)
            action = 'permanently deleted'
        else:
            # Soft delete - deactivate user
            success = user_manager.deactivate_user(number)
            action = 'deactivated'
        
        if success:
            logging.info(f"Admin {action} user: {user.name} ({number})")
            return jsonify({
                'status': 'success',
                'message': f'User {action} successfully',
                'action': action,
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({'status': 'error', 'message': f'Failed to {action.split()[0]} user'}), 400
            
    except Exception as e:
        logging.error(f"Admin delete user error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_bp.route('/admin/database/users/<number>/reactivate', methods=['POST'])
def admin_reactivate_user(number):
    """Admin endpoint to reactivate a deactivated user"""
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        # Check if user exists
        user = user_manager.get_user_by_number(number)
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Reactivate user
        updated_user = user_manager.update_user(number, active=True)
        if updated_user:
            logging.info(f"Admin reactivated user: {user.name} ({number})")
            return jsonify({
                'status': 'success',
                'message': 'User reactivated successfully',
                'user': updated_user.to_dict()
            }), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to reactivate user'}), 400
            
    except Exception as e:
        logging.error(f"Admin reactivate user error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_bp.route('/admin/database/users/bulk-action', methods=['POST'])
def admin_bulk_action():
    """Admin endpoint for bulk actions on users"""
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        action = data.get('action')
        user_numbers = data.get('user_numbers', [])
        
        if not action or not user_numbers:
            return jsonify({'status': 'error', 'message': 'Missing action or user_numbers'}), 400
        
        results = []
        
        for number in user_numbers:
            try:
                if action == 'deactivate':
                    success = user_manager.deactivate_user(number)
                elif action == 'reactivate':
                    success = user_manager.update_user(number, active=True) is not None
                elif action == 'delete':
                    success = user_manager.delete_user(number)
                else:
                    results.append({'number': number, 'success': False, 'error': 'Invalid action'})
                    continue
                
                results.append({'number': number, 'success': success})
                
            except Exception as e:
                results.append({'number': number, 'success': False, 'error': str(e)})
        
        successful = len([r for r in results if r['success']])
        failed = len(results) - successful
        
        logging.info(f"Admin bulk {action}: {successful} successful, {failed} failed")
        
        return jsonify({
            'status': 'success',
            'message': f'Bulk {action} completed',
            'results': results,
            'summary': {
                'total': len(results),
                'successful': successful,
                'failed': failed
            }
        }), 200
        
    except Exception as e:
        logging.error(f"Admin bulk action error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

