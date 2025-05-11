import time
import logging

# Dictionary to store recently processed message contents with timestamps
# This is used to prevent duplicate processing of the same message
RECENT_MESSAGES = {}
# Time window in seconds (2 minutes) for message deduplication
MESSAGE_DEDUPLICATION_WINDOW = 120

# Define the list of allowed WhatsApp group IDs
# These are the groups from which the application will process messages
ALLOWED_GROUP_IDS = [
    "120363027964709829@g.us",  #Logistics
    "120363418341850743@g.us",  #Suceeder 
    "120363047500602968@g.us",  #DeliverMyMotor Jobs
    "447970999007-1605100552@g.us",  #RoadBuddy
    "120363253724037366@g.us",  #Hook & Tow 24/7 Live breakdown&Transportation
    "120363237643056676@g.us",  #ReadyBuddy
    "120363202924994425@g.us",  #TOW'D Recovery & Mobile Mechanic Jobs
    "120363280694146648@g.us",  #Recovery Group 247 (Only Approved Members)
    "120363106696007089@g.us",  #Midlands Recovery & Transport nationwide live job
    "120363080837066139@g.us",  #UK Vehicle Deliveries
    "120363187784105179@g.us",  #X Car Recovery Jobs
    "120363287378726347@g.us",  #Caravan Towing Services
    "447535620336-1610361222@g.us",  #Uk Caravan Deliveries
    "120363418461600560@g.us",  #Ai filter test
]

def cleanup_old_messages():
    """
    Remove expired messages from the deduplication cache
    Messages older than MESSAGE_DEDUPLICATION_WINDOW seconds are removed
    """
    current_time = time.time()
    # Find keys (message contents) that have expired
    expired_keys = [key for key, timestamp in RECENT_MESSAGES.items() 
                   if current_time - timestamp > MESSAGE_DEDUPLICATION_WINDOW]
    
    # Delete expired keys from dictionary
    for key in expired_keys:
        del RECENT_MESSAGES[key]
    
    if expired_keys:
        logging.info(f"Cleaned up {len(expired_keys)} expired messages")

def is_duplicate_message(message_content):
    """
    Check if a message has been processed recently to avoid duplicates
    
    Args:
        message_content (str): Content of the message to check
        
    Returns:
        bool: True if message is a duplicate, False otherwise
    """
    current_time = time.time()
    
    # Check if this message content exists in our recent messages
    if message_content in RECENT_MESSAGES:
        # If it exists and is within our time window, it's a duplicate
        if current_time - RECENT_MESSAGES[message_content] <= MESSAGE_DEDUPLICATION_WINDOW:
            return True
    
    # If not a duplicate, add/update the message in our cache
    RECENT_MESSAGES[message_content] = current_time
    return False

def extract_message_content(message):
    """
    Extract content from different message types
    
    Args:
        message (dict): Message data from webhook
        
    Returns:
        str: Message content or None if unsupported type
    """
    message_type = message.get('type', 'UnknownMessageType')
    
    if message_type == 'text':
        return message.get('text', {}).get('body', 'No content Text')
    elif message_type == 'image':
        return message.get('image', {}).get('caption', 'No content Image')
    elif message_type == 'video':
        return message.get('video', {}).get('caption', 'No content Video')
    elif message_type == 'link_preview':
        return message.get('link_preview', {}).get('body', 'No content link')
    else:
        logging.warning(f"Unsupported message type: {message_type}")
        return None
