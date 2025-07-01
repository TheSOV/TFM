"""
Docker Compose Validator

Validates Docker Compose files using 'docker compose config' command.
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

def validate_docker_compose(file_path: str) -> Dict[str, Any]:
    """
    Validate a Docker Compose file.
    
    Args:
        file_path: Path to the docker-compose.yml or compose.yml file
        
    Returns:
        Dict containing validation results with structure:
        {
            'success': bool,
            'summary': {
                'valid': int,     # Number of valid services (1 if validation succeeds)
                'invalid': int,   # Number of invalid services (0 or 1)
                'errors': int     # Number of validation errors
            },
            'errors': [
                {
                    'type': str,     # Error type (e.g., 'ValidationError', 'YAMLError')
                    'message': str,  # Error message
                    'path': str,     # Path to the file
                    'service': str   # Service name if available, None otherwise
                },
                ...
            ]
        }
    """
    result = {
        "success": True,
        "summary": {"valid": False, "errors": 0},
        "errors": []
    }
    
    try:
        # Convert to Path and ensure it's a file
        compose_path = Path(file_path)
        if not compose_path.exists():
            result["success"] = False
            result["summary"]["valid"] = False
            result["summary"]["errors"] = 1
            result["errors"].append({
                "type": "FileNotFoundError",
                "message": f"Docker Compose file not found: {file_path}",
                "service": None
            })
            return result
            
        if not compose_path.is_file():
            result["success"] = False
            result["summary"]["valid"] = False
            result["summary"]["errors"] = 1
            result["errors"].append({
                "type": "ValueError",
                "message": f"Path is not a file: {file_path}",
                "service": None
            })
            return result
            
        # Get the parent directory for the working directory
        project_dir = compose_path.parent
            
        # Run docker compose config to validate the file
        cmd = [
            "docker", "compose",
            "-f", str(compose_path.absolute()),
            "config"
        ]
        
        process = subprocess.run(
            cmd,
            cwd=str(project_dir.absolute()),
            capture_output=True,
            text=True,
            check=True
        )
        
        # If we get here, validation was successful
        result["summary"]["valid"] = True
        
    except subprocess.CalledProcessError as e:
        result["success"] = False
        result["summary"]["valid"] = False
        result["summary"]["errors"] = 1
        
        # Try to extract service name from error message if possible
        service_name = None
        error_message = e.stderr.strip()
        
        result["errors"].append({
            "type": "ValidationError",
            "message": error_message,
            "service": service_name
        })
        
    except Exception as e:
        result["success"] = False
        result["summary"]["valid"] = False
        result["summary"]["errors"] = 1
        result["errors"].append({
            "type": type(e).__name__,
            "message": str(e),
            "service": None
        })
    
    return result