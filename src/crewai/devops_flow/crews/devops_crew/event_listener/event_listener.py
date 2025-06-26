"""Event listener for tracking CrewAI task and tool execution.

This module provides a listener that captures various events from the CrewAI system
and records them to the blackboard for monitoring and debugging purposes.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from crewai.utilities.events import (
    TaskStartedEvent,
    TaskCompletedEvent,
)
from crewai.utilities.events.base_event_listener import BaseEventListener

from src.crewai.devops_flow.blackboard.Blackboard import Blackboard
from src.crewai.devops_flow.blackboard.utils.Events import Event

def safe_get_attr(obj, attr: str, default: Any = None) -> Any:
    """Safely get an attribute from an object with a default value."""
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default

def extract_task_data(source: Any, event: Any, event_type: str) -> Dict[str, str]:
    """Extract and format task data from event objects."""
    # Get timestamp and format as HH:MM:SS
    timestamp = safe_get_attr(event, 'timestamp', datetime.now(timezone.utc))
    if isinstance(timestamp, (int, float)):
        timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    elif not isinstance(timestamp, datetime):
        timestamp = datetime.now(timezone.utc)
    
    # Extract agent info from the source (the Task object)
    agent = safe_get_attr(source, 'agent', {})
    agent_role = safe_get_attr(agent, 'role', 'No Agent')
    
    # Extract task info from the source (the Task object)
    description = safe_get_attr(source, 'description', 'No description')
    
    # Prepare base data
    data = {
        'timestamp': timestamp.isoformat(),
        'type': event_type,
        'agent_role': agent_role,
        'task_description': description,
    }
    
    # Add output for completed tasks from the event object
    if event_type == 'task_completed':
        output = safe_get_attr(event, 'output', '')
        data['output'] = str(output) if output else 'No output'
    
    return data


class DevopsEventListener(BaseEventListener):
    """Listener for tracking task and tool execution events.
    
    This listener captures various events from the CrewAI system and records them
    to the provided blackboard instance for monitoring and debugging purposes.
    """
    
    def __init__(self, blackboard: Blackboard):
        """Initialize the listener with a blackboard instance.
        
        Args:
            blackboard: The blackboard instance to record events to.
        """
        super().__init__()
        self.blackboard = blackboard

    def setup_listeners(self, crewai_event_bus):
        """Set up event listeners for the CrewAI event bus.
        
        Args:
            crewai_event_bus: The event bus to register listeners with.
        """
        # Task Events
        @crewai_event_bus.on(TaskCompletedEvent)
        def on_task_completed(source, event):
            """Handle task completed events."""
            try:
                # Extract and format task data
                task_data = extract_task_data(source, event, 'task_completed')
                
                event_obj = Event(data=task_data)
                self.blackboard.events.add_event(event_obj)
                
            except Exception as e:
                print(f"Error in on_task_completed: {str(e)}")


