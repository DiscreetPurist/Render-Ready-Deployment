# This file makes the services directory a Python package
from services.whatsapp_service import send_whapi_request, set_hook, send_message
from services.openai_service import generate_response_for_user, get_openai_client

__all__ = [
    'send_whapi_request', 
    'set_hook', 
    'send_message',
    'generate_response_for_user',
    'get_openai_client'
]
