# This file makes the routes directory a Python package
from routes.webhook_routes import webhook_bp
from routes.user_routes import user_bp
from routes.website_routes import website_bp

__all__ = ['webhook_bp', 'user_bp', 'website_bp']
