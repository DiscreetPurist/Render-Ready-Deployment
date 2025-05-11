from flask import Blueprint, render_template, request, jsonify, redirect, url_for
import os
import logging
import stripe

# Create a Blueprint for website routes
website_bp = Blueprint('website', __name__, 
                      template_folder='../website/templates',
                      static_folder='../website/static')

# Initialize Stripe with API key from environment variables
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@website_bp.route('/website', methods=['GET'])
def index():
    """Home page"""
    return render_template('index.html')

@website_bp.route('/website/pricing', methods=['GET'])
def pricing():
    """Pricing page"""
    return render_template('pricing.html')

@website_bp.route('/website/signup', methods=['GET'])
def signup():
    """Signup page"""
    stripe_public_key = os.getenv('STRIPE_PUBLIC_KEY')
    return render_template('signup.html', stripe_public_key=stripe_public_key)

@website_bp.route('/website/contact', methods=['GET'])
def contact():
    """Contact page"""
    return render_template('contact.html')

@website_bp.route('/website/thank-you', methods=['GET'])
def thank_you():
    """Thank you page after successful subscription"""
    return render_template('thank_you.html')

@website_bp.route('/create-subscription', methods=['POST'])
def create_subscription():
    """
    Handle subscription creation
    1. Create or retrieve Stripe customer
    2. Create subscription
    3. Create user in our system
    """
    try:
        # Import user_manager here to avoid circular imports
        from app import user_manager
        
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
            
        payment_method_id = data.get('paymentMethodId')
        customer_data = data.get('customerData')
        
        if not payment_method_id or not customer_data:
            return jsonify({'status': 'error', 'message': 'Missing required data'}), 400
        
        # Validate Stripe configuration
        stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
        stripe_price_id = os.getenv('STRIPE_PRICE_ID')
        
        if not stripe_secret_key or not stripe_price_id:
            logging.error("Stripe configuration missing")
            return jsonify({'status': 'error', 'message': 'Stripe configuration missing'}), 500
        
        # Create or retrieve a customer in Stripe
        try:
            customers = stripe.Customer.list(email=customer_data['email'])
            if customers.data:
                customer = customers.data[0]
                # Update customer with new payment method
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=customer.id
                )
                stripe.Customer.modify(
                    customer.id,
                    invoice_settings={
                        'default_payment_method': payment_method_id
                    }
                )
            else:
                customer = stripe.Customer.create(
                    email=customer_data['email'],
                    name=customer_data['name'],
                    phone=customer_data['phone'],
                    payment_method=payment_method_id,
                    invoice_settings={
                        'default_payment_method': payment_method_id
                    }
                )
        except stripe.error.StripeError as e:
            logging.error(f"Stripe customer error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 400
        
        # Create the subscription
        try:
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {
                        'price': stripe_price_id  # Monthly subscription price ID
                    }
                ],
                expand=['latest_invoice.payment_intent'],
                payment_behavior='default_incomplete',
                payment_settings={
                    'payment_method_types': ['card'],
                    'save_default_payment_method': 'on_subscription'
                }
            )
        except stripe.error.StripeError as e:
            logging.error(f"Stripe subscription error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 400
        
        # Check if payment requires additional action
        if subscription.latest_invoice.payment_intent.status == 'requires_action':
            return jsonify({
                'status': 'requires_action',
                'clientSecret': subscription.latest_invoice.payment_intent.client_secret
            })
        
        # If payment is successful, create user in our system
        if subscription.status == 'active' or subscription.status == 'trialing':
            # Add user to our system
            user = user_manager.add_user(
                name=customer_data['name'],
                number=customer_data['phone'],
                location=customer_data['location'],
                range_miles=int(customer_data['range']),
                stripe_customer_id=customer.id,
                subscription_id=subscription.id
            )
            
            return jsonify({
                'status': 'success',
                'message': 'Subscription created successfully',
                'subscription': subscription.id
            })
        
        return jsonify({
            'status': 'error',
            'message': f'Subscription creation failed: {subscription.status}'
        })
        
    except stripe.error.StripeError as e:
        logging.error(f"Stripe error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logging.error(f"Subscription error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@website_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Handle Stripe webhook events
    - subscription.created: Log the creation
    - invoice.paid: Ensure user is active
    - customer.subscription.deleted: Deactivate user
    """
    try:
        # Import user_manager here to avoid circular imports
        from app import user_manager
        
        payload = request.data
        sig_header = request.headers.get('Stripe-Signature')
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        if not webhook_secret:
            logging.error("Stripe webhook secret not configured")
            return jsonify({'status': 'error', 'message': 'Webhook secret not configured'}), 500
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            # Invalid payload
            logging.error(f"Invalid webhook payload: {e}")
            return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            logging.error(f"Invalid webhook signature: {e}")
            return jsonify({'status': 'error', 'message': 'Invalid signature'}), 400
        
        # Handle specific events
        event_type = event['type']
        logging.info(f"Processing Stripe webhook event: {event_type}")
        
        if event_type == 'customer.subscription.deleted':
            subscription = event['data']['object']
            customer_id = subscription['customer']
            
            # Find the user by Stripe customer ID
            user = user_manager.get_user_by_stripe_customer_id(customer_id)
            if user:
                # Deactivate the user
                user_manager.deactivate_user(user.number)
                logging.info(f"Deactivated user {user.name} due to subscription cancellation")
            else:
                logging.warning(f"User not found for customer {customer_id}")
            
        elif event_type == 'invoice.paid':
            invoice = event['data']['object']
            subscription_id = invoice['subscription']
            customer_id = invoice['customer']
            
            # Find all users with this customer ID
            users = [u for u in user_manager.get_users(active_only=False) 
                    if u.stripe_customer_id == customer_id]
            
            for user in users:
                # Ensure user is active
                if not getattr(user, 'active', True):
                    user_manager.update_user(user.number, active=True)
                    logging.info(f"Reactivated user {user.name} due to invoice payment")
        
        return jsonify({'status': 'success', 'message': f'Webhook processed: {event_type}'}), 200
    
    except Exception as e:
        logging.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500
