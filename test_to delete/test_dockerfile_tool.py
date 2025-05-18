"""
Dockerfile Syntax Validation Tool Test

Validates Docker Compose config using 'docker compose config --quiet' via subprocess.
Uses the shared Docker Compose project in the temp directory, following project conventions.
"""
import os
from pathlib import Path
import subprocess
import sys
from typing import Union


def validate_compose_project(path: Union[str, Path]) -> dict:
    """
    Validate a docker-compose project using 'docker compose config --quiet'.

    Args:
        path (str | Path): Path to the directory containing the docker-compose.yml file.
    Returns:
        dict: Validation result with 'success' and 'error' keys.
    """
    cmd = [
        "docker", "compose",
        "--project-directory", str(Path(path).resolve()),
        "config", "--quiet"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return {"success": True, "error": None}
    return {"success": False, "error": result.stderr.strip() or "compose validation failed"}


if __name__ == "__main__":
    # Example usage: validate temp/docker-compose.yml project directory
    project_dir = Path(__file__).parent / "temp"
    result = validate_compose_project(project_dir)
    if result["success"]:
        print("Compose config is valid ")
    else:
        sys.exit(f"  {result['error']}")
