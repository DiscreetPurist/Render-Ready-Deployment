from flask import Flask
from dotenv import load_dotenv
import os
import logging
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Initialize Sentry for error tracking (if configured)
sentry_dsn = os.getenv('SENTRY_DSN')
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.5,
        environment=os.getenv('ENVIRONMENT', 'production')
    )
    logging.info("Sentry initialized for error tracking")

# Load environment variables from .env file in development
# In production (Render), environment variables are set in the dashboard
if os.environ.get('RENDER') != 'true':
    load_dotenv()
    logging.info("Loaded environment variables from .env file")

# Initialize Flask application
app = Flask(__name__)

# Initialize user manager - this loads existing users from storage
from managers.user_manager import UserManager
storage_file = os.environ.get('USER_STORAGE_FILE', 'users.json')
user_manager = UserManager(storage_file=storage_file)

# Register blueprints
from routes.webhook_routes import webhook_bp
from routes.user_routes import user_bp
from routes.website_routes import website_bp

app.register_blueprint(webhook_bp)
app.register_blueprint(user_bp)
app.register_blueprint(website_bp)

# Set up webhook only in development or when explicitly requested
if os.environ.get('SETUP_WEBHOOK', 'false').lower() == 'true':
    from services.whatsapp_service import set_hook
    set_hook()
    logging.info("WhatsApp webhook set up")

# Application entry point
if __name__ == '__main__':
    # Determine port based on environment variables
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    # Log application startup
    logging.info(f"Starting Recovery Manager on port {port} (debug={debug})")
    
    # Start the Flask application
    app.run(host='0.0.0.0', port=port, debug=debug)
