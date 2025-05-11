from flask import Blueprint, request, jsonify
import logging
from utils.message_utils import cleanup_old_messages, is_duplicate_message, extract_message_content, ALLOWED_GROUP_IDS
from services.openai_service import generate_response_for_user
from services.whatsapp_service import send_whapi_request, set_hook

# Create a Blueprint for webhook routes
webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/hook/messages', methods=['POST'])
def handle_new_messages():
    """
    Process incoming webhook messages from WhatsApp API
    This is the main entry point where messages are processed and forwarded to users
    
    Returns:
        tuple: HTTP status response (200 OK or 500 Error)
    """
    try:
        # Import user_manager here to avoid circular imports
        from app import user_manager
        
        # Clean up old messages from the cache
        cleanup_old_messages()
        
        # Get the messages from the webhook payload
        messages = request.json.get('messages', [])
        
        if not messages:
            logging.info("Received webhook with no messages")
            return jsonify({"status": "success", "message": "No messages to process"}), 200
        
        logging.info(f"Processing {len(messages)} messages from webhook")
        
        # Process each message in the list
        for message in messages:
            # Skip messages sent by you (the bot)
            if message.get('from_me'):
                continue
                
            # Extract sender information
            group_sender_id = message.get('chat_id', 'UnknownGroupID')
            group_sender_name = message.get('chat_name', 'UnknownGroupName')
            member_id = message.get('from', 'UnknownMemberID')
            member_name = message.get('from_name', 'UnknownMemberName')
            
            logging.info(f"Processing message from group: {group_sender_name}")
            
            # Check if this group is allowed
            if group_sender_id not in ALLOWED_GROUP_IDS:
                logging.info(f"Skipping message from non-allowed group: {group_sender_name}")
                continue
            
            # Extract message content
            message_content = extract_message_content(message)
            if not message_content:
                continue
            
            logging.info(f"Message content: {message_content[:50]}...")
            
            # Check if this is a duplicate message
            if is_duplicate_message(message_content):
                logging.info(f"Skipping duplicate message: {message_content[:50]}...")
                continue
            
            # Prepare the job message to be sent to users
            job_message = f"From Group: {group_sender_name}\nFrom member: +{member_id} \n\n{message_content}"
            
            # Process for each user - check if the job is relevant for them
            active_users = user_manager.get_users(active_only=True)
            logging.info(f"Checking job relevance for {len(active_users)} active users")
            
            for user in active_users:
                # Generate AI response for this specific user based on their location/range
                ai_response = generate_response_for_user(message_content, user)
                
                # If job is found for this user (within their range), send notification
                if "JOB FOUND" in ai_response:
                    # Prepare message parameters for WhatsApp API
                    sender = {
                        'to': f"{user.number}@c.us",  # Format for WhatsApp number
                        'body': "JOB FOUND \n\n" + job_message
                    }
                    # Send the message via WhatsApp API
                    response = send_whapi_request('messages/text', sender)
                    if 'error' in response:
                        logging.error(f"Failed to send notification to {user.name}: {response['error']}")
                    else:
                        logging.info(f"Notification sent to {user.name} ({user.number}) for job")
        
        return jsonify({"status": "success", "message": "Messages processed"}), 200
    
    except Exception as e:
        logging.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@webhook_bp.route('/setup-webhook', methods=['GET'])
def setup_webhook():
    """
    Endpoint to manually trigger webhook setup
    
    Returns:
        tuple: HTTP status response (200 OK or 500 Error)
    """
    try:
        result = set_hook()
        if 'error' in result:
            return jsonify({"status": "error", "message": result['error']}), 500
        return jsonify({"status": "success", "message": "Webhook set up successfully", "result": result}), 200
    except Exception as e:
        logging.error(f"Error setting up webhook: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@webhook_bp.route('/', methods=['GET'])
def index():
    """
    Root endpoint - simple health check
    
    Returns:
        tuple: HTTP status response (200 OK)
    """
    return jsonify({
        "status": "success", 
        "message": "Recovery Manager API is running",
        "version": "1.0.0"
    }), 200
