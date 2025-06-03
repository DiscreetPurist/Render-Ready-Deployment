from flask import Blueprint, jsonify, render_template_string
import os
import stripe
import logging

# Create a Blueprint for debug routes (remove in production)
debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug/stripe-config', methods=['GET'])
def check_stripe_config():
    """Debug endpoint to check Stripe configuration"""
    try:
        # Check environment variables
        stripe_secret = os.getenv('STRIPE_SECRET_KEY')
        stripe_public = os.getenv('STRIPE_PUBLIC_KEY')
        stripe_price_id = os.getenv('STRIPE_PRICE_ID')
        stripe_webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        config_status = {
            'stripe_secret_key': 'Set' if stripe_secret else 'Missing',
            'stripe_public_key': 'Set' if stripe_public else 'Missing',
            'stripe_price_id': stripe_price_id if stripe_price_id else 'Missing',
            'stripe_webhook_secret': 'Set' if stripe_webhook_secret else 'Missing'
        }
        
        # Test Stripe API connection
        if stripe_secret:
            stripe.api_key = stripe_secret
            try:
                # Try to retrieve the price
                if stripe_price_id:
                    price = stripe.Price.retrieve(stripe_price_id)
                    price_info = {
                        'id': price.id,
                        'amount': price.unit_amount,
                        'currency': price.currency,
                        'recurring': price.recurring.interval if price.recurring else None,
                        'product': price.product,
                        'active': price.active
                    }
                else:
                    price_info = 'Price ID not set'
                    
                # Test API connection
                account = stripe.Account.retrieve()
                api_status = 'Connected'
                
            except stripe.error.StripeError as e:
                price_info = f'Error: {str(e)}'
                api_status = f'Error: {str(e)}'
        else:
            price_info = 'Cannot check - no API key'
            api_status = 'Cannot check - no API key'
        
        return jsonify({
            'status': 'success',
            'config': config_status,
            'api_connection': api_status,
            'price_details': price_info
        }), 200
        
    except Exception as e:
        logging.error(f"Debug endpoint error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@debug_bp.route('/debug/list-prices', methods=['GET'])
def list_prices():
    """List all available prices in your Stripe account"""
    try:
        stripe_secret = os.getenv('STRIPE_SECRET_KEY')
        if not stripe_secret:
            return jsonify({'status': 'error', 'message': 'Stripe secret key not set'}), 500
        
        stripe.api_key = stripe_secret
        
        # List all prices
        prices = stripe.Price.list(limit=10, active=True)
        
        price_list = []
        for price in prices.data:
            price_list.append({
                'id': price.id,
                'amount': price.unit_amount,
                'currency': price.currency,
                'recurring': price.recurring.interval if price.recurring else 'one-time',
                'product': price.product,
                'active': price.active
            })
        
        return jsonify({
            'status': 'success',
            'prices': price_list
        }), 200
        
    except stripe.error.StripeError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@debug_bp.route('/debug/users', methods=['GET'])
def view_users():
    """Simple HTML page to view all users"""
    try:
        from app import user_manager
        
        if user_manager is None:
            return "Service not ready", 503
        
        users = user_manager.get_users(active_only=False)
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Users Database View</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .active { color: green; font-weight: bold; }
                .inactive { color: red; }
            </style>
        </head>
        <body>
            <h1>Users Database ({{ user_count }} total)</h1>
            <table>
                <tr>
                    <th>Name</th>
                    <th>Number</th>
                    <th>Location</th>
                    <th>Range</th>
                    <th>Status</th>
                    <th>Stripe Customer</th>
                    <th>Created</th>
                </tr>
                {% for user in users %}
                <tr>
                    <td>{{ user.name }}</td>
                    <td>{{ user.number }}</td>
                    <td>{{ user.location }}</td>
                    <td>{{ user.range_miles }} miles</td>
                    <td class="{{ 'active' if user.active else 'inactive' }}">
                        {{ 'Active' if user.active else 'Inactive' }}
                    </td>
                    <td>{{ user.stripe_customer_id or 'None' }}</td>
                    <td>{{ user.created_at }}</td>
                </tr>
                {% endfor %}
            </table>
            
            <h2>Quick Stats</h2>
            <ul>
                <li>Total Users: {{ user_count }}</li>
                <li>Active Users: {{ active_count }}</li>
                <li>Inactive Users: {{ inactive_count }}</li>
            </ul>
        </body>
        </html>
        """
        
        active_users = [u for u in users if getattr(u, 'active', True)]
        
        return render_template_string(html_template, 
                                    users=users,
                                    user_count=len(users),
                                    active_count=len(active_users),
                                    inactive_count=len(users) - len(active_users))
        
    except Exception as e:
        logging.error(f"Error viewing users: {e}")
        return f"Error: {str(e)}", 500

@debug_bp.route('/debug/database-test', methods=['GET'])
def test_database():
    """Test database connection and show table info"""
    try:
        from config.database import db_config
        
        with db_config.get_connection() as conn:
            with conn.cursor() as cursor:
                # Test connection
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                
                # Check if users table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'users'
                    );
                """)
                table_exists = cursor.fetchone()[0]
                
                # Get table info if it exists
                table_info = []
                if table_exists:
                    cursor.execute("""
                        SELECT column_name, data_type, is_nullable 
                        FROM information_schema.columns 
                        WHERE table_name = 'users'
                        ORDER BY ordinal_position;
                    """)
                    table_info = cursor.fetchall()
                
                # Count users
                user_count = 0
                if table_exists:
                    cursor.execute("SELECT COUNT(*) FROM users;")
                    user_count = cursor.fetchone()[0]
        
        return jsonify({
            'status': 'success',
            'database_version': version,
            'users_table_exists': table_exists,
            'user_count': user_count,
            'table_structure': [
                {
                    'column': col[0],
                    'type': col[1],
                    'nullable': col[2]
                } for col in table_info
            ]
        })
        
    except Exception as e:
        logging.error(f"Database test error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
