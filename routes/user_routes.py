from flask import Blueprint, request, jsonify
import logging

# Create a Blueprint for user API routes
user_bp = Blueprint('user', __name__)

@user_bp.route('/api/users', methods=['POST'])
def api_add_user():
    """
    API endpoint to add a new user
    """
    try:
        # Import user_manager from app module
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        name = data.get('name')
        number = data.get('number')
        location = data.get('location')
        range_miles = data.get('range_miles')
        stripe_customer_id = data.get('stripe_customer_id')
        subscription_id = data.get('subscription_id')
        
        # Validate required fields
        if not all([name, number, location, range_miles]):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
        # Add the user    
        user = user_manager.add_user(
            name=name,
            number=number,
            location=location,
            range_miles=int(range_miles),
            stripe_customer_id=stripe_customer_id,
            subscription_id=subscription_id
        )
        
        # Return success response
        return jsonify({
            'status': 'success', 
            'message': 'User added successfully',
            'user': user.to_dict()
        }), 201
            
    except Exception as e:
        logging.error(f"Error adding user: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@user_bp.route('/api/users', methods=['GET'])
def api_get_users():
    """
    API endpoint to get all users
    """
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        users = user_manager.get_users(active_only=active_only)
        return jsonify({
            'status': 'success',
            'count': len(users),
            'users': [user.to_dict() for user in users]
        }), 200
    except Exception as e:
        logging.error(f"Error getting users: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@user_bp.route('/api/users/<number>', methods=['GET'])
def api_get_user(number):
    """
    API endpoint to get a specific user by WhatsApp number
    """
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        user = user_manager.get_user_by_number(number)
        if user:
            return jsonify({
                'status': 'success',
                'user': user.to_dict()
            }), 200
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    except Exception as e:
        logging.error(f"Error getting user: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@user_bp.route('/api/users/<number>', methods=['PUT'])
def api_update_user(number):
    """
    API endpoint to update a user
    """
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        user = user_manager.update_user(number, **data)
        if user:
            return jsonify({
                'status': 'success',
                'message': 'User updated successfully',
                'user': user.to_dict()
            }), 200
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    except Exception as e:
        logging.error(f"Error updating user: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@user_bp.route('/api/users/<number>', methods=['DELETE'])
def api_delete_user(number):
    """
    API endpoint to delete a user
    """
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
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    except Exception as e:
        logging.error(f"Error deleting user: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500
