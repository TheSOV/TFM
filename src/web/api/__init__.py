"""
API Blueprint for the DevopsFlow web server.

This module exposes the API blueprint which is registered with routes.
"""

from flask import Blueprint

# Create and export the API blueprint
api_bp = Blueprint('api', __name__)

# Import routes after creating the blueprint to avoid circular imports
# The routes will register themselves with the blueprint
from . import routes  # noqa
