from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
import os
import logging
import stripe
from routes.auth_routes import require_auth

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
    stripe_public_key = os.getenv('STRIPE_PUBLIC_KEY')
    stripe_price_id = os.getenv('STRIPE_PRICE_ID')
    return render_template('pricing.html', 
                         stripe_public_key=stripe_public_key,
                         stripe_price_id=stripe_price_id)

@website_bp.route('/website/signup', methods=['GET'])
def signup():
    """Signup page"""
    stripe_public_key = os.getenv('STRIPE_PUBLIC_KEY')
    stripe_price_id = os.getenv('STRIPE_PRICE_ID')
    return render_template('signup.html', 
                         stripe_public_key=stripe_public_key,
                         stripe_price_id=stripe_price_id)

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
    Handle subscription creation with improved error handling
    """
    try:
        from app import user_manager
        
        if user_manager is None:
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
            
        payment_method_id = data.get('paymentMethodId')
        customer_data = data.get('customerData')
        
        if not payment_method_id or not customer_data:
            return jsonify({'status': 'error', 'message': 'Missing required data'}), 400
        
        # Validate required customer data
        required_fields = ['name', 'email', 'phone', 'location', 'range']
        for field in required_fields:
            if not customer_data.get(field):
                return jsonify({'status': 'error', 'message': f'Missing {field}'}), 400
        
        # Validate Stripe configuration
        stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
        stripe_price_id = os.getenv('STRIPE_PRICE_ID')
        
        if not stripe_secret_key or not stripe_price_id:
            logging.error("Stripe configuration missing")
            return jsonify({'status': 'error', 'message': 'Payment system not configured'}), 500
        
        # Create or retrieve customer
        try:
            # Check if customer already exists
            customers = stripe.Customer.list(
                email=customer_data['email'],
                limit=1
            )
            
            if customers.data:
                customer = customers.data[0]
                logging.info(f"Found existing customer: {customer.id}")
                
                # Attach new payment method
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=customer.id
                )
                
                # Update default payment method
                stripe.Customer.modify(
                    customer.id,
                    invoice_settings={
                        'default_payment_method': payment_method_id
                    }
                )
            else:
                # Create new customer
                customer = stripe.Customer.create(
                    email=customer_data['email'],
                    name=customer_data['name'],
                    phone=customer_data['phone'],
                    payment_method=payment_method_id,
                    invoice_settings={
                        'default_payment_method': payment_method_id
                    },
                    metadata={
                        'location': customer_data['location'],
                        'range': str(customer_data['range'])
                    }
                )
                logging.info(f"Created new customer: {customer.id}")
                
        except stripe.error.StripeError as e:
            logging.error(f"Stripe customer error: {e}")
            return jsonify({'status': 'error', 'message': f'Customer creation failed: {str(e)}'}), 400
        
        # Check for existing active subscription
        try:
            existing_subs = stripe.Subscription.list(
                customer=customer.id,
                status='active',
                limit=1
            )
            
            if existing_subs.data:
                return jsonify({
                    'status': 'error',
                    'message': 'Customer already has an active subscription'
                }), 400
                
        except stripe.error.StripeError as e:
            logging.error(f"Error checking existing subscriptions: {e}")
        
        # Create the subscription - FIXED VERSION
        try:
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{
                    'price': stripe_price_id
                }],
                payment_behavior='default_incomplete',
                payment_settings={
                    'payment_method_types': ['card'],
                    'save_default_payment_method': 'on_subscription'
                },
                # Only expand latest_invoice, not payment_intent
                expand=['latest_invoice'],
                metadata={
                    'location': customer_data['location'],
                    'range': str(customer_data['range'])
                }
            )
            
            logging.info(f"Created subscription: {subscription.id}")
            
        except stripe.error.StripeError as e:
            logging.error(f"Stripe subscription error: {e}")
            return jsonify({'status': 'error', 'message': f'Subscription creation failed: {str(e)}'}), 400
        
        # Handle different subscription statuses
        if subscription.status == 'active':
            # Subscription is immediately active (no payment required or trial)
            try:
                user = user_manager.add_user(
                    name=customer_data['name'],
                    number=customer_data['phone'],
                    location=customer_data['location'],
                    range_miles=int(customer_data['range']),
                    stripe_customer_id=customer.id,
                    subscription_id=subscription.id
                )
                
                logging.info(f"Created user: {user.name} ({user.number})")
                
                return jsonify({
                    'status': 'success',
                    'message': 'Subscription created successfully',
                    'subscription_id': subscription.id,
                    'customer_id': customer.id
                })
                
            except Exception as e:
                logging.error(f"Error creating user: {e}")
                # Cancel the subscription if user creation fails
                try:
                    stripe.Subscription.delete(subscription.id)
                except:
                    pass
                return jsonify({'status': 'error', 'message': 'User creation failed'}), 500
                
        elif subscription.status == 'incomplete':
            # Payment is required
            latest_invoice = subscription.latest_invoice
            
            # Check if latest_invoice has payment_intent
            if hasattr(latest_invoice, 'payment_intent') and latest_invoice.payment_intent:
                payment_intent = latest_invoice.payment_intent
                
                if payment_intent.status == 'requires_action':
                    return jsonify({
                        'status': 'requires_action',
                        'client_secret': payment_intent.client_secret,
                        'subscription_id': subscription.id
                    })
                elif payment_intent.status == 'succeeded':
                    # Payment succeeded, create user
                    try:
                        user = user_manager.add_user(
                            name=customer_data['name'],
                            number=customer_data['phone'],
                            location=customer_data['location'],
                            range_miles=int(customer_data['range']),
                            stripe_customer_id=customer.id,
                            subscription_id=subscription.id
                        )
                        
                        logging.info(f"Created user: {user.name} ({user.number})")
                        
                        return jsonify({
                            'status': 'success',
                            'message': 'Subscription created successfully',
                            'subscription_id': subscription.id,
                            'customer_id': customer.id
                        })
                        
                    except Exception as e:
                        logging.error(f"Error creating user: {e}")
                        try:
                            stripe.Subscription.delete(subscription.id)
                        except:
                            pass
                        return jsonify({'status': 'error', 'message': 'User creation failed'}), 500
                else:
                    return jsonify({
                        'status': 'error',
                        'message': f'Payment failed: {payment_intent.status}'
                    }), 400
            else:
                # No payment_intent, might be a trial or free subscription
                try:
                    user = user_manager.add_user(
                        name=customer_data['name'],
                        number=customer_data['phone'],
                        location=customer_data['location'],
                        range_miles=int(customer_data['range']),
                        stripe_customer_id=customer.id,
                        subscription_id=subscription.id
                    )
                    
                    logging.info(f"Created user: {user.name} ({user.number})")
                    
                    return jsonify({
                        'status': 'success',
                        'message': 'Subscription created successfully',
                        'subscription_id': subscription.id,
                        'customer_id': customer.id
                    })
                    
                except Exception as e:
                    logging.error(f"Error creating user: {e}")
                    try:
                        stripe.Subscription.delete(subscription.id)
                    except:
                        pass
                    return jsonify({'status': 'error', 'message': 'User creation failed'}), 500
        else:
            return jsonify({
                'status': 'error',
                'message': f'Subscription creation failed: {subscription.status}'
            }), 400
        
    except Exception as e:
        logging.error(f"Subscription creation error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@website_bp.route('/confirm-payment', methods=['POST'])
def confirm_payment():
    """
    Handle payment confirmation after 3D Secure authentication
    """
    try:
        from app import user_manager
        
        data = request.json
        payment_intent_id = data.get('payment_intent_id')
        subscription_id = data.get('subscription_id')
        customer_data = data.get('customerData')
        
        if not payment_intent_id or not subscription_id:
            return jsonify({'status': 'error', 'message': 'Missing payment information'}), 400
        
        # Retrieve the payment intent to check status
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if payment_intent.status == 'succeeded':
            # Retrieve subscription to get customer info
            subscription = stripe.Subscription.retrieve(subscription_id)
            customer = stripe.Customer.retrieve(subscription.customer)
            
            # Create user in our system
            try:
                user = user_manager.add_user(
                    name=customer_data['name'],
                    number=customer_data['phone'],
                    location=customer_data['location'],
                    range_miles=int(customer_data['range']),
                    stripe_customer_id=customer.id,
                    subscription_id=subscription.id
                )
                
                logging.info(f"Created user after payment confirmation: {user.name}")
                
                return jsonify({
                    'status': 'success',
                    'message': 'Payment confirmed and subscription activated'
                })
                
            except Exception as e:
                logging.error(f"Error creating user after payment confirmation: {e}")
                return jsonify({'status': 'error', 'message': 'User creation failed'}), 500
        else:
            return jsonify({
                'status': 'error',
                'message': f'Payment not completed: {payment_intent.status}'
            }), 400
            
    except Exception as e:
        logging.error(f"Payment confirmation error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@website_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events with improved logging
    """
    try:
        from app import user_manager
        
        if user_manager is None:
            logging.error("User manager not initialized for webhook")
            return jsonify({'status': 'error', 'message': 'Service not ready'}), 503
        
        payload = request.data
        sig_header = request.headers.get('Stripe-Signature')
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        if not webhook_secret:
            logging.error("Stripe webhook secret not configured")
            return jsonify({'status': 'error', 'message': 'Webhook not configured'}), 500
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            logging.error(f"Invalid webhook payload: {e}")
            return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError as e:
            logging.error(f"Invalid webhook signature: {e}")
            return jsonify({'status': 'error', 'message': 'Invalid signature'}), 400
        
        # Handle specific events
        event_type = event['type']
        logging.info(f"Processing Stripe webhook: {event_type}")
        
        if event_type == 'customer.subscription.created':
            subscription = event['data']['object']
            customer_id = subscription['customer']
            logging.info(f"Subscription created for customer: {customer_id}")
            
        elif event_type == 'customer.subscription.deleted':
            subscription = event['data']['object']
            customer_id = subscription['customer']
            
            # Find and deactivate user
            user = user_manager.get_user_by_stripe_customer_id(customer_id)
            if user:
                user_manager.deactivate_user(user.number)
                logging.info(f"Deactivated user {user.name} due to subscription cancellation")
            else:
                logging.warning(f"User not found for customer {customer_id}")
            
        elif event_type == 'invoice.paid':
            invoice = event['data']['object']
            customer_id = invoice['customer']
            
            # Ensure user is active
            user = user_manager.get_user_by_stripe_customer_id(customer_id)
            if user and not getattr(user, 'active', True):
                user_manager.update_user(user.number, active=True)
                logging.info(f"Reactivated user {user.name} due to successful payment")
                
        elif event_type == 'invoice.payment_failed':
            invoice = event['data']['object']
            customer_id = invoice['customer']
            
            # Optionally deactivate user after failed payment
            user = user_manager.get_user_by_stripe_customer_id(customer_id)
            if user:
                logging.warning(f"Payment failed for user {user.name}")
                # You might want to send a notification or deactivate after multiple failures
        
        return jsonify({'status': 'success', 'message': f'Webhook processed: {event_type}'}), 200
    
    except Exception as e:
        logging.error(f"Webhook processing error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@website_bp.route('/cancel-subscription', methods=['POST'])
def cancel_subscription():
    """
    Allow users to cancel their subscription
    """
    try:
        from app import user_manager
        
        data = request.json
        phone_number = data.get('phone_number')
        
        if not phone_number:
            return jsonify({'status': 'error', 'message': 'Phone number required'}), 400
        
        # Find user
        user = user_manager.get_user_by_number(phone_number)
        if not user or not user.subscription_id:
            return jsonify({'status': 'error', 'message': 'Subscription not found'}), 404
        
        # Cancel subscription in Stripe
        try:
            subscription = stripe.Subscription.delete(user.subscription_id)
            logging.info(f"Cancelled subscription {user.subscription_id} for user {user.name}")
            
            return jsonify({
                'status': 'success',
                'message': 'Subscription cancelled successfully'
            })
            
        except stripe.error.StripeError as e:
            logging.error(f"Error cancelling subscription: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 400
        
    except Exception as e:
        logging.error(f"Subscription cancellation error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@website_bp.route('/admin', methods=['GET'])
@require_auth
def admin_dashboard():
    """Admin dashboard page - protected by authentication"""
    return render_template('admin_dashboard.html')



