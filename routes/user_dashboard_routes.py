from flask import Blueprint, render_template, jsonify, request
import os
import stripe
import logging
from routes.user_auth_routes import require_user_auth

# Create a Blueprint for user dashboard
user_dashboard_bp = Blueprint('user_dashboard', __name__, 
                             template_folder='../website/templates')

@user_dashboard_bp.route('/dashboard', methods=['GET'])
@require_user_auth
def dashboard():
    """User dashboard page"""
    return render_template('user_dashboard.html')

@user_dashboard_bp.route('/login', methods=['GET'])
def login_page():
    """User login page"""
    return render_template('user_login.html')

@user_dashboard_bp.route('/api/user/subscription-status', methods=['GET'])
@require_user_auth
def get_subscription_status():
    """Get detailed subscription status from Stripe"""
    try:
        from app import user_manager
        
        user = user_manager.get_user_by_email(request.headers.get('user_email') or 
                                            getattr(request, 'user_email', None) or
                                            session.get('user_email'))
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        if not user.subscription_id:
            return jsonify({
                'status': 'success',
                'subscription': {
                    'status': 'none',
                    'message': 'No active subscription'
                }
            }), 200
        
        # Get subscription details from Stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        try:
            subscription = stripe.Subscription.retrieve(user.subscription_id)
            
            return jsonify({
                'status': 'success',
                'subscription': {
                    'id': subscription.id,
                    'status': subscription.status,
                    'current_period_start': subscription.current_period_start,
                    'current_period_end': subscription.current_period_end,
                    'cancel_at_period_end': subscription.cancel_at_period_end,
                    'canceled_at': subscription.canceled_at,
                    'amount': subscription.items.data[0].price.unit_amount if subscription.items.data else 0,
                    'currency': subscription.items.data[0].price.currency if subscription.items.data else 'gbp',
                    'interval': subscription.items.data[0].price.recurring.interval if subscription.items.data else 'month'
                }
            }), 200
            
        except stripe.error.StripeError as e:
            logging.error(f"Stripe error getting subscription: {e}")
            return jsonify({
                'status': 'success',
                'subscription': {
                    'status': 'error',
                    'message': 'Unable to retrieve subscription details'
                }
            }), 200
            
    except Exception as e:
        logging.error(f"Get subscription status error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@user_dashboard_bp.route('/api/user/cancel-subscription', methods=['POST'])
@require_user_auth
def cancel_subscription():
    """Cancel user subscription"""
    try:
        from app import user_manager
        
        data = request.json
        password = data.get('password') if data else None
        
        if not password:
            return jsonify({'status': 'error', 'message': 'Password required to cancel subscription'}), 400
        
        user = user_manager.get_user_by_email(session.get('user_email'))
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Verify password
        if not user.check_password(password):
            return jsonify({'status': 'error', 'message': 'Incorrect password'}), 401
        
        if not user.subscription_id:
            return jsonify({'status': 'error', 'message': 'No active subscription to cancel'}), 400
        
        # Cancel subscription in Stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        try:
            subscription = stripe.Subscription.delete(user.subscription_id)
            logging.info(f"Cancelled subscription {user.subscription_id} for user {user.email}")
            
            return jsonify({
                'status': 'success',
                'message': 'Subscription cancelled successfully',
                'subscription': {
                    'status': subscription.status,
                    'canceled_at': subscription.canceled_at
                }
            }), 200
            
        except stripe.error.StripeError as e:
            logging.error(f"Error cancelling subscription: {e}")
            return jsonify({'status': 'error', 'message': f'Failed to cancel subscription: {str(e)}'}), 400
        
    except Exception as e:
        logging.error(f"Cancel subscription error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
