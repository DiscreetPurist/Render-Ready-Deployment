import os
import logging
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Flask app
app = Flask(__name__)

# Initialize database and user manager
user_manager = None

def initialize_app():
    """Initialize the application with database"""
    global user_manager
    
    try:
        # Import here to avoid circular imports
        from database.schema import initialize_database
        from managers.user_manager_postgres import UserManager
        
        # Initialize database schema
        if not initialize_database():
            raise Exception("Failed to initialize database")
        
        # Create user manager instance
        user_manager = UserManager()
        
        logging.info("Application initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"Failed to initialize application: {e}")
        return False

# Initialize the app
if not initialize_app():
    logging.error("Application startup failed")
    # Don't exit in production, let health check handle it

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
        if user_manager is None:
            return {
                'status': 'unhealthy',
                'error': 'User manager not initialized'
            }, 500
            
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

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return {
        'status': 'success',
        'message': 'Recovery Manager API is running',
        'version': '2.0.0'
    }, 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
