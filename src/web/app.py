"""
Main Flask application module for the DevopsFlow web server.

This module initializes the Flask application and configures the API routes.
"""

import os
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS

# Import API blueprint
from src.web.api import api_bp

# Import state to avoid circular imports
from src.web.state import devops_flow_thread, devops_flow

# Get the absolute path to the static directory
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

def create_app() -> Flask:
    """Create and configure the Flask application.
    
    Returns:
        Flask: The configured Flask application
    """
    app = Flask(__name__, 
                static_folder=STATIC_DIR,
                static_url_path='/static')
    
    # Enable CORS for all routes with more permissive settings for development
    CORS(app, 
         resources={
             r"/api/*": {
                 "origins": "*",
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True
             },
             r"/*": {
                 "origins": "*"
             }
         })
    
    # Add CORS headers to all responses
    @app.after_request
    def after_request(response):
        """Add security and CORS headers to all responses."""
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    
    # Register API blueprint
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Route to serve the main index.html file
    @app.route('/')
    def serve_index():
        """Serve the main index.html file."""
        return send_from_directory(app.static_folder, 'index.html')

    # Catch-all for SPA routing
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors by serving the index.html for non-API routes."""
        if not request.path.startswith('/api/'):
            return send_from_directory(app.static_folder, 'index.html')
        return e
    
    return app


app = create_app()
