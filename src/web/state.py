"""Module to hold shared application state to avoid circular imports."""
import threading
from typing import Optional
from src.crewai.devops_flow.DevopsFlow import DevopsFlow

# Global state
devops_flow_thread: Optional[threading.Thread] = None
devops_flow: Optional[DevopsFlow] = None
