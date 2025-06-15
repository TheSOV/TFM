"""
API routes for the DevopsFlow web server.

This module contains all the route handlers for the API endpoints.
"""

import threading
from typing import Dict, Any

from flask import jsonify, request

from src.crewai.devops_flow.DevopsFlow import DevopsFlow
import src.services_registry.services as services
from src.web import state
from . import api_bp


@api_bp.route('/init', methods=['POST'])
def init_devops_flow() -> Dict[str, Any]:
    """
    Initialize and start the DevopsFlow with the given prompt.
    
    Returns:
        Dict containing the status of the operation and any relevant messages.
    """
    
    
    # Check if DevopsFlow is already running
    if state.devops_flow_thread and state.devops_flow_thread.is_alive():
        return {
            'status': 'error',
            'message': 'DevopsFlow is already running'
        }, 400

    # Get the prompt from the request
    data = request.get_json()
    if not data or 'prompt' not in data:
        return {
            'status': 'error',
            'message': 'No prompt provided'
        }, 400

    prompt = data['prompt']

    try:
        # Initialize DevopsFlow; it will get the blackboard from the service registry
        state.devops_flow = DevopsFlow(user_request=prompt)

        def run_devops_flow():
            # The kickoff method starts the main process
            state.devops_flow.kickoff()

        
        state.devops_flow_thread = threading.Thread(target=run_devops_flow)
        state.devops_flow_thread.daemon = True
        state.devops_flow_thread.start()

        return {
            'status': 'success',
            'message': 'DevopsFlow started successfully',
            'prompt': prompt
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to start DevopsFlow: {str(e)}'
        }, 500


@api_bp.route('/blackboard', methods=['GET'])
def get_blackboard() -> Dict[str, Any]:
    """
    Get the current state of the blackboard.
    
    Returns:
        Dict containing the blackboard content and status.
    """
    try:
        blackboard = services.get("blackboard")
        content = blackboard.model_dump()
        
        return {
            'status': 'success',
            'blackboard': content
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to read blackboard: {str(e)}'
        }, 500


@api_bp.route('/status', methods=['GET'])
def get_status() -> Dict[str, Any]:
    """
    Get the current status of the DevopsFlow.
    
    Returns:
        Dict containing the status of the DevopsFlow.
    """
    is_running = state.devops_flow_thread and state.devops_flow_thread.is_alive()
    return {
        'status': 'running' if is_running else 'stopped',
        'is_running': is_running
    }


@api_bp.route('/kill', methods=['POST'])
def kill_devops_flow() -> Dict[str, Any]:
    """
    Signal the running DevopsFlow process to stop and attempt to clean up.
    """
    if not state.devops_flow_thread or not state.devops_flow_thread.is_alive():
        return {
            'status': 'error',
            'message': 'No DevopsFlow process is currently running.'
        }, 400

    message = "DevopsFlow process signaled to stop."
    try:
        kill_event = services.get("kill_signal_event")
        kill_event.set()
        # Attempt to wait for the thread to finish
        state.devops_flow_thread.join(timeout=3600.0) # Wait up to 1 hour for graceful termination 

        if state.devops_flow_thread.is_alive():
            message = 'DevopsFlow process was signaled to stop but did not terminate gracefully within the timeout. It might still be running in the background.'
        else:
            message = 'DevopsFlow process stopped successfully after signal.'
            
    except Exception as e:
        message = f'An error occurred while trying to stop DevopsFlow: {str(e)}. The process may still be running.'
        # Log the exception for server-side review
        # logger.error(f"Error during kill_devops_flow: {str(e)}", exc_info=True) # Assuming logger is configured
    finally:
        # CRITICAL: Always clear state variables to allow a new flow to start
        # This effectively orphans the thread if it's still running, but from the app's perspective, it's stopped.
        state.devops_flow_thread = None
        state.devops_flow = None
        # The kill_signal_event in the registry should be cleared by the DevopsFlow process
        # itself upon successful termination or at the start of a new flow.

    return {
        'status': 'success',
        'message': message
    }
