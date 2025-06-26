"""
Popeye Scan Client

A client for running Popeye scans on Kubernetes clusters to detect potential issues
with deployments, pods, configurations, and other Kubernetes resources.
"""
import json
import subprocess
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PopeyeScanClient:
    """
    Client for running Popeye scans on Kubernetes clusters.
    
    This client provides methods to run Popeye scans and parse their results.
    """
    
    def __init__(self, popeye_path: str = "popeye"):
        """
        Initialize the PopeyeScanClient.
        
        Args:
            popeye_path: Path to the Popeye executable (default: 'popeye')
        """
        self.popeye_path = popeye_path
    
    def _check_popeye_installed(self) -> bool:
        """Check if Popeye is installed and accessible."""
        try:
            subprocess.run(
                [self.popeye_path, "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def run_scan(self, namespace: str) -> Dict[str, Any]:
        """
        Run a Popeye scan on the specified namespace.
        
        Args:
            namespace: Kubernetes namespace to scan
            
        Returns:
            Dict containing the scan results in JSON format
            
        Raises:
            RuntimeError: If the Popeye command fails, is not found, or returns invalid output
        """
        # First check if Popeye is installed
        if not self._check_popeye_installed():
            error_msg = (
                f"Popeye executable not found at '{self.popeye_path}'. "
                "Please ensure Popeye is installed and available in your PATH, "
                "or set the POPEYE_PATH environment variable to the correct location.\n"
                "You can download Popeye from: https://github.com/derailed/popeye"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        cmd = [
            self.popeye_path,
            "-n", namespace,
            "-o", "json",
            "--force-exit-zero"  # Always return exit code 0 to handle issues in the results
        ]
        
        try:
            logger.info(f"Running Popeye scan on namespace: {namespace}")
            
            # Run the Popeye command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the JSON output
            try:
                scan_results = json.loads(result.stdout)
                return scan_results
                
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse Popeye output as JSON: {str(e)}"
                logger.error(f"{error_msg}. Output: {result.stdout[:500]}...")
                raise RuntimeError(error_msg) from e
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Popeye scan failed: {e.stderr or 'No error details available'}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
            
        except FileNotFoundError as e:
            error_msg = (
                f"Popeye executable not found at '{self.popeye_path}'. "
                f"Error: {str(e)}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Unexpected error running Popeye scan: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e