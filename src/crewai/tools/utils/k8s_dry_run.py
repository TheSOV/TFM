"""
Kubernetes Dry-Run Validator

Validates Kubernetes manifest files using 'kubectl apply --dry-run=server' command.
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

def k8s_dry_run(
    file_path: Path,
    kubeconfig: Optional[str] = None,
    namespace: Optional[str] = None,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate Kubernetes manifests using 'kubectl apply --dry-run=server'.
    
    Args:
        file_path: Path to the Kubernetes manifest file or directory
        kubeconfig: Path to kubeconfig file (optional)
        namespace: Namespace to use for validation (optional)
        context: Kubernetes context to use (optional)
    
    Returns:
        Dict containing validation results with structure:
        {
            "success": bool,           # Whether the dry-run was successful
            "output": str,             # Full command output (on success)
            "error": str               # Error message if any
        }
    """
    # Initialize result structure
    result = {
        "success": False,
        "error": ""  # Single error string instead of a list
    }

    
    # Check if kubectl is available
    try:
        subprocess.run(
            ["kubectl", "version", "--client", "--output=yaml"],
            capture_output=True,
            text=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        result["error"] = (
            "kubectl is not installed or not in PATH. "
            "Please install kubectl and ensure it's available in your PATH."
        )
        return result
    
    # Build the kubectl command
    cmd = ["kubectl", "apply", "--dry-run=server", "-f", str(file_path)]
    
    # Add optional flags
    if kubeconfig:
        cmd.extend(["--kubeconfig", str(kubeconfig)])
    if namespace:
        cmd.extend(["--namespace", namespace])
    if context:
        cmd.extend(["--context", context])
    
    # Don't add -o json as it's not supported with --dry-run=server
    # The output will be in the format: "<resource> <name> created (dry run)"
    
    try:
        # Run the command
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False  # We'll handle non-zero exit codes
        )

        # Extract base directories from the file_path
        path_parts = file_path.parts
        base_dir_1 = path_parts[0] if len(path_parts) > 0 else None
        base_dir_2 = path_parts[1] if len(path_parts) > 1 else None
        
        # Combine stdout and stderr for the result
        full_output = []
        # if process.stdout:
        #     full_output.append("=== STDOUT ===")
        #     full_output.append(process.stdout)
        if process.stderr:
            # full_output.append("\n=== STDERR ===")
            full_output.append(process.stderr)
            
        output_text = " ".join(full_output).replace(base_dir_1, "").replace(base_dir_2, "").replace("\\\\\\\\", "")
        
        if process.returncode == 0:
            # For successful dry-run, include the output in the result
            result["success"] = True
            result["output"] = output_text
        else:
            # For errors, include the full output as a single error message
            result["error"] = f"kubectl dry-run failed with output: {output_text}"
    
    except Exception as e:
        result["error"] = f"An unexpected error occurred: {str(e)}"
    
    return result