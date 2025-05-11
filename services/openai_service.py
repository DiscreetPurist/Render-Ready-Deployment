import os
import logging
from openai import OpenAI
from openai.error import OpenAIError

# Initialize OpenAI client with API key from environment variables
def get_openai_client():
    """
    Get OpenAI client with API key from environment variables
    
    Returns:
        OpenAI: OpenAI client
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("OpenAI API key not configured")
        return None
    
    return OpenAI(api_key=api_key)

def generate_response_for_user(message_body, user):
    """
    Use OpenAI to determine if a job is within a user's range
    
    Args:
        message_body (str): Job message content
        user (User): User object with location and range
        
    Returns:
        str: AI response ("JOB FOUND" or "NIL")
    """
    client = get_openai_client()
    if not client:
        logging.error("Failed to initialize OpenAI client")
        return "NIL"  # Default to no match if API is not available
    
    try:
        # Create prompt with user's specific location and range
        prompt = f"You will receive potential vehicle recovery job leads as your user input. If any of the locations or postcodes in the user message is within {user.range_miles} miles of {user.location} please reply with: JOB FOUND, Else reply with: NIL."
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1",
            temperature=1.0,
            messages=[
                {"role": "developer", "content": prompt},
                {"role": "user", "content": message_body}
            ]
        )

        # Extract response text
        ai_response = response.choices[0].message.content
        
        # Log response for debugging
        logging.info(f"AI response for {user.name}: {ai_response}")
        logging.info(f"Total tokens used for {user.name}: {response.usage.total_tokens}")
        
        return ai_response
    
    except OpenAIError as e:
        logging.error(f"OpenAI API error: {e}")
        return "NIL"  # Default to no match if API fails
    
    except Exception as e:
        logging.error(f"Unexpected error in OpenAI service: {e}")
        return "NIL"  # Default to no match if something goes wrong
