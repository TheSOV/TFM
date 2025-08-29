"""
API routes for the DevopsFlow web server.

This module contains all the route handlers for the API endpoints.
"""

import traceback
import threading
from typing import Dict, Any

from flask import jsonify, request

from src.crewai.devops_flow.DevopsFlow import DevopsFlow
import src.services_registry.services as services
from src.web import state
import asyncio
from typing import Optional, Dict, Any
from flask import jsonify, request
import traceback

from . import api_bp
from src.crewai.devops_flow.crews.devops_crew.ConsultCrew import ConsultCrew

import logging
logger = logging.getLogger(__name__)

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
            try:
                # The kickoff method starts the main process
                print("DevOps flow thread started.")
                asyncio.run(state.devops_flow.kickoff(), debug=True)
                print("DevOps flow thread finished successfully.")
            except asyncio.CancelledError as e:
                print("TOP-LEVEL CANCEL:", e)
                traceback.print_exc()
            except BaseException as e:
                print("TOP-LEVEL CRASH:", e)
                traceback.print_exc()
            finally:
                print("DevopsFlow thread is terminating.")

        
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
def get_status():
    """
    Get the current status of the DevopsFlow.
    
    Returns:
        JSON object containing the detailed status of the DevopsFlow.
    """
    is_running = state.devops_flow_thread and state.devops_flow_thread.is_alive()
    status_message = 'Process stopped'
    is_waiting_for_input = False
    step_name = ''

    if is_running:
        # Default status if blackboard is not available
        status_message = 'Running...'
        if state.devops_flow:
            try:
                blackboard = services.get("blackboard")
                # Use the phase as the main status message, fallback if empty
                status_message = blackboard.phase or 'Initializing...'
                
                interaction_status_string = blackboard.interaction.status
                if interaction_status_string and interaction_status_string.startswith('waiting_for_input:'):
                    is_waiting_for_input = True
                    # Extract step name, e.g., from "waiting_for_input:first_approach"
                    step_name = interaction_status_string.split(':', 1)[1]
            except Exception as e:
                # This can happen if the thread is running but blackboard service is not ready
                status_message = 'Initializing...'
                # Optionally log the error for debugging:
                # print(f"Could not get detailed status from blackboard: {e}")

    return jsonify({
        'status': status_message,
        'is_running': is_running,
        'is_waiting_for_input': is_waiting_for_input,
        'step_name': step_name
    })


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


@api_bp.route('/interaction/mode', methods=['POST'])
def set_interaction_mode():
    """
    Set the interaction mode for the DevopsFlow.
    """
    data = request.get_json()
    if not data or 'mode' not in data:
        return jsonify({'status': 'error', 'message': 'Mode not provided'}), 400
    
    mode = data['mode']
    if mode not in ['assisted', 'automated']:
        return jsonify({'status': 'error', 'message': "Invalid mode. Must be 'assisted' or 'automated'."}), 400

    try:
        blackboard = services.get("blackboard")
        blackboard.interaction.mode = mode
        return jsonify({'status': 'success', 'message': f'Interaction mode set to {mode}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to set interaction mode: {str(e)}'}), 500


@api_bp.route('/interaction/status', methods=['GET'])
def get_interaction_status():
    """
    Get the current interaction status from the blackboard.
    """
    try:
        blackboard = services.get("blackboard")
        user_input_wait_event = services.get("user_input_wait_event")
        
        interaction_status = blackboard.interaction.model_dump()
        interaction_status['is_waiting'] = user_input_wait_event.is_set()
        
        return jsonify({
            'status': 'success',
            'interaction': interaction_status
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to get interaction status: {str(e)}'}), 500


@api_bp.route('/interaction/resume', methods=['POST'])
def resume_flow():
    """
    Resume the DevopsFlow by providing feedback and setting the resume event.
    """
    data = request.get_json()
    feedback = data.get('feedback', '')

    try:
        blackboard = services.get("blackboard")
        user_input_received_event = services.get("user_input_received_event")
        
        user_input_wait_event = services.get("user_input_wait_event")
        if not user_input_wait_event.is_set():
            return jsonify({'status': 'error', 'message': 'The system is not currently waiting for user input.'}), 409

        blackboard.interaction.user_feedback = feedback
        user_input_received_event.set()
        
        return jsonify({'status': 'success', 'message': 'Flow resume signal sent.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to resume flow: {str(e)}'}), 500


@api_bp.route('/consult-crew/chat', methods=['POST'])
def chat_with_crew() -> Dict[str, Any]:
    """
    Handle chat requests with ConsultCrew.
    
    Expects JSON with:
    - question (str): The user's question/input
    - conversation_id (str, optional): ID of an existing conversation
    
    Returns:
        JSON response with status, answer, and conversation_id
    """
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
    question = data.get('question')
    conversation_id = data.get('conversation_id')
    
    if not question or not isinstance(question, str):
        return jsonify({'status': 'error', 'message': 'Valid question is required'}), 400

    try:
        # Create a new ConsultCrew instance for this request
        crew = ConsultCrew().crew()
        
        # Execute the task with the user's question
        answer = crew.kickoff(inputs={'user_request': question, 'context': None})
        
        return jsonify({
            'status': 'success',
            'answer': answer.raw,
            'conversation_id': conversation_id or 'new'
        })
        
    except Exception as e:
        logger.error(f'Error in chat_with_crew: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'An error occurred while processing your request'
        }), 500
