import os
import requests
import logging
from requests_toolbelt.multipart.encoder import MultipartEncoder

def send_whapi_request(endpoint, params=None, method='POST'):
    """
    Send a request to the WhatsApp API
    
    Args:
        endpoint (str): API endpoint path
        params (dict): Parameters to include in request
        method (str): HTTP method (GET, POST, etc.)
        
    Returns:
        dict: JSON response from the API
    """
    token = os.getenv('TOKEN')
    api_url = os.getenv('API_URL')
    
    if not token or not api_url:
        logging.error("WhatsApp API credentials not configured")
        return {"error": "WhatsApp API credentials not configured"}
    
    headers = {
        'Authorization': f"Bearer {token}"
    }
    url = f"{api_url}/{endpoint}"
    
    try:
        # Handle different request types
        if params:
            if 'media' in params:
                # Handle media uploads (images, files)
                details = params.pop('media').split(';')
                with open(details[0], 'rb') as file:
                    m = MultipartEncoder(fields={**params, 'media': (details[0], file, details[1])})
                    headers['Content-Type'] = m.content_type
                    response = requests.request(method, url, data=m, headers=headers)
            elif method == 'GET':
                # Handle GET requests
                response = requests.get(url, params=params, headers=headers)
            else:
                # Handle other requests with JSON body
                headers['Content-Type'] = 'application/json'
                response = requests.request(method, url, json=params, headers=headers)
        else:
            # Handle requests without parameters
            response = requests.request(method, url, headers=headers)
        
        response_json = response.json()
        logging.info(f"WhatsApp API response: {response.status_code}")
        return response_json
    
    except requests.exceptions.RequestException as e:
        logging.error(f"WhatsApp API request failed: {e}")
        return {"error": str(e)}

def set_hook():
    """Set up webhook for receiving messages from WhatsApp API"""
    bot_url = os.getenv('BOT_URL')
    if not bot_url:
        logging.error("BOT_URL not configured, cannot set webhook")
        return {"error": "BOT_URL not configured"}
    
    logging.info(f"Setting up webhook to {bot_url}")
    settings = {
        'webhooks': [
            {
                'url': bot_url,  # URL where this app is hosted
                'events': [
                    {'type': "messages", 'method': "post"}  # Listen for messages
                ],
                'mode': "method"
            }
        ],
        'offline_mode': True  # Enable offline mode
    }
    return send_whapi_request('settings', settings, 'PATCH')

def send_message(to_number, message):
    """
    Send a text message via WhatsApp
    
    Args:
        to_number (str): Recipient's WhatsApp number
        message (str): Message content
        
    Returns:
        dict: API response
    """
    params = {
        'to': f"{to_number}@c.us",
        'body': message
    }
    return send_whapi_request('messages/text', params)
