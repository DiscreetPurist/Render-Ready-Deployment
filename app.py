import os
import logging
from flask import Flask, jsonify
import secrets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Flask app
app = Flask(__name__)

# Configure session
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 28800  # 8 hours in seconds

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

# Import and register blueprints with error handling
try:
    from routes.user_routes import user_bp
    app.register_blueprint(user_bp)
except ImportError as e:
    logging.error(f"Failed to import user_routes: {e}")

try:
    from routes.website_routes import website_bp
    app.register_blueprint(website_bp)
except ImportError as e:
    logging.error(f"Failed to import website_routes: {e}")

try:
    from routes.webhook_routes import webhook_bp
    app.register_blueprint(webhook_bp)
except ImportError as e:
    logging.error(f"Failed to import webhook_routes: {e}")

try:
    from routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp)
except ImportError as e:
    logging.error(f"Failed to import admin_routes: {e}")

try:
    from routes.debug_routes import debug_bp
    app.register_blueprint(debug_bp)
except ImportError as e:
    logging.error(f"Failed to import debug_routes: {e}")

try:
    from routes.backup_routes import backup_bp
    app.register_blueprint(backup_bp)
except ImportError as e:
    logging.error(f"Failed to import backup_routes: {e}")

try:
    from routes.wordpress_routes import wordpress_bp
    app.register_blueprint(wordpress_bp)
except ImportError as e:
    logging.error(f"Failed to import wordpress_routes: {e}")

try:
    from routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp)
except ImportError as e:
    logging.error(f"Failed to import auth_routes: {e}")

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
