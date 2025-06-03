from flask import Blueprint, request, jsonify
import os
import logging
import stripe

# Create a Blueprint for webhook routes
webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events
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

@webhook_bp.route('/hook/messages', methods=['POST'])
def receive_messages():
    """
    Handle incoming group messages
    """
    try:
        # Get the JSON data from the request
        data = request.get_json()
        
        if not data:
            logging.warning("Received empty message data")
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        # Log the incoming message for debugging
        logging.info(f"Received group message: {data}")
        
        # Extract message information
        message_type = data.get('type', 'unknown')
        message_content = data.get('content', '')
        sender = data.get('sender', 'unknown')
        timestamp = data.get('timestamp')
        
        # Process the message based on type
        if message_type == 'text':
            logging.info(f"Text message from {sender}: {message_content}")
        elif message_type == 'image':
            logging.info(f"Image message from {sender}")
        elif message_type == 'location':
            logging.info(f"Location message from {sender}")
        else:
            logging.info(f"Unknown message type '{message_type}' from {sender}")
        
        # Here you can add your specific message processing logic
        # For example:
        # - Store the message in database
        # - Forward to specific users
        # - Trigger notifications
        # - Process commands
        
        return jsonify({
            'status': 'success', 
            'message': 'Message received and processed',
            'received_type': message_type
        }), 200
    
    except Exception as e:
        logging.error(f"Error processing group message: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500
