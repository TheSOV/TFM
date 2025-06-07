"""
Docker Compose Validator

Validates Docker Compose files using 'docker compose config' command.
This checks for syntax errors, missing services, invalid configurations,
and other issues in docker-compose.yaml files.
"""
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

def docker_dry_run(
    compose_file: Union[str, Path],
    project_directory: Optional[Union[str, Path]] = None,
    env_file: Optional[Union[str, Path]] = None,
    profiles: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Validate a Docker Compose file using 'docker compose config'.
    
    Args:
        compose_file: Path to the docker-compose.yaml file (str or Path)
        project_directory: Directory containing the compose file (default: same as compose_file directory)
        env_file: Path to .env file (optional)
        profiles: List of profiles to include (optional)
    
    Returns:
        Dict containing validation results with structure:
        {
            "success": bool,           # Whether the validation was successful
            "output": str,             # Full command output (on success)
            "error": str,              # Error message if any
            "validated_config": str    # The resolved compose configuration (on success)
        }
    """
    # Convert paths to Path objects if they are strings
    compose_file = Path(compose_file) if isinstance(compose_file, str) else compose_file
    if project_directory is not None:
        project_directory = Path(project_directory) if isinstance(project_directory, str) else project_directory
    if env_file is not None:
        env_file = Path(env_file) if isinstance(env_file, str) else env_file
    
    result = {
        "success": False
    }

    # Check if docker compose is available
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        result["error"] = (
            "Docker Compose is not installed or not in PATH. "
            "Please install Docker Desktop or Docker Compose and ensure it's available in your PATH."
        )
        return result

    # Verify compose file exists
    if not compose_file.exists():
        result["error"] = f"Docker Compose file not found at: {compose_file}"
        return result

    # Set project directory to compose file's directory if not specified
    if project_directory is None:
        project_directory = compose_file.parent

    # Build the docker compose command
    cmd = ["docker", "compose", "--file", str(compose_file)]
    
    # Add env file if specified
    if env_file:
        if not env_file.exists():
            result["error"] = f"Environment file not found: {env_file}"
            return result
        cmd.extend(["--env-file", str(env_file)])
    
    # Add profiles if specified
    if profiles:
        cmd.extend(["--profile", ",".join(profiles)])
    
    # Add the config command and options
    cmd.extend(["config", "--format", "yaml"])

    try:
        # Run the command
        process = subprocess.run(
            cmd,
            cwd=str(project_directory),
            capture_output=True,
            text=True,
            check=False  # We'll handle non-zero exit codes
        )
        
        # Combine stdout and stderr
        full_output = []
        if process.stdout:
            full_output.append(process.stdout)
        if process.stderr:
            full_output.append(process.stderr)
            
        output_text = "\n".join(full_output).strip()
        
        if process.returncode == 0:
            result["success"] = True
        else:
            result["error"] = f"Docker Compose validation failed: {output_text}"
    
    except Exception as e:
        result["error"] = f"An unexpected error occurred: {str(e)}"
    
    return result
