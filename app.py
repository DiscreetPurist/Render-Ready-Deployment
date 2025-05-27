import os
import logging
from flask import Flask
from database.schema import initialize_database
from managers.user_manager_postgres import UserManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Flask app
app = Flask(__name__)

# Initialize database and user manager
try:
    # Initialize database schema
    if not initialize_database():
        raise Exception("Failed to initialize database")
    
    # Create user manager instance
    user_manager = UserManager()
    
    logging.info("Application initialized successfully")
    
except Exception as e:
    logging.error(f"Failed to initialize application: {e}")
    raise

# Import and register blueprints
from routes.user_routes import user_bp
from routes.website_routes import website_bp
from routes.webhook_routes import webhook_bp

app.register_blueprint(user_bp)
app.register_blueprint(website_bp)
app.register_blueprint(webhook_bp)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        user_count = user_manager.get_user_count()
        return {
            'status': 'healthy',
            'database': 'connected',
            'users': user_count
        }, 200
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }, 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

