"""
Popeye Scan Tool for CrewAI

This module provides a tool for running Popeye scans on Kubernetes clusters
through the CrewAI framework.
"""
import json
import logging
from typing import Type, Optional

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .utils.popeye_scan import PopeyeScanClient

logger = logging.getLogger(__name__)

class PopeyeScanInput(BaseModel):
    """Input schema for Popeye scan tool."""
    namespace: str = Field(
        default="all",
        description="Kubernetes namespace to scan (default: 'all' for all namespaces)"
    )

class PopeyeScanTool(BaseTool):
    """Tool to run Popeye scans on Kubernetes clusters."""
    
    name: str = "popeye_scan"
    description: str = (
        "Run a Popeye scan on a Kubernetes cluster to detect potential issues "
        "with deployments, pods, configurations, and other resources. "
        "Returns a detailed report of findings and recommendations."
    )
    args_schema: Type[BaseModel] = PopeyeScanInput
    
    _popeye_client: PopeyeScanClient = None
    
    def __init__(self, popeye_path: str = "popeye", **kwargs):
        """
        Initialize the PopeyeScanTool.
        
        Args:
            popeye_path: Path to the Popeye executable (default: 'popeye')
            **kwargs: Additional arguments to pass to the parent class
        """
        super().__init__(**kwargs)
        self._popeye_client = PopeyeScanClient(popeye_path=popeye_path)
    
    def _run(self, namespace: str = "all") -> str:
        """
        Run a Popeye scan on the specified namespace.
        
        Args:
            namespace: Kubernetes namespace to scan (default: 'all')
            
        Returns:
            str: JSON string containing the scan results
        """
        try:
            # Run the scan
            scan_results = self._popeye_client.run_scan(namespace=namespace)
            
            # Convert the results to a pretty-printed JSON string
            return json.dumps(scan_results, indent=2)
            
        except Exception as e:
            error_msg = f"Failed to run Popeye scan: {str(e)}"
            logger.error(error_msg)
            return error_msg
