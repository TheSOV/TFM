from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class Event(BaseModel):
    """Base class for all events.
    
    Attributes:
        event_type: Type of the event.
        timestamp: When the event occurred.
        source: Source of the event (e.g., agent name, tool name).
        data: Additional event-specific data.
    """
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event-specific data"
    )


class Events(BaseModel):
    """Collection of events in the system.
    
    Attributes:
        events: List of all recorded events.
    """
    events: List[Event] = Field(
        default_factory=list,
        description="List of all recorded events"
    )
    
    def add_event(self, event: Event) -> None:
        """Add a new event to the collection, ensuring the list does not exceed 10 events.

        Args:
            event: The event to add.
        """
        # Add the new event to the end of the list
        self.events.append(event)
        
        # If the list exceeds 10 events, remove the oldest one (from the beginning)
        if len(self.events) > 10:
            self.events.pop(0)
    
    def get_events(self) -> List[Event]:
        """Get all events, sorted with the most recent first.
        
        Returns:
            List of all recorded events.
        """
        # Assuming timestamp is in the data dictionary and is a sortable string (ISO format)
        return sorted(
            self.events, 
            key=lambda e: e.data.get('timestamp', ''), 
            reverse=True
        )
    
    def clear_events(self) -> None:
        """Clear all events."""
        self.events = []