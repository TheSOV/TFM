"""
Kubernetes Manifest Validator

Provides validation for Kubernetes manifest files using the kubernetes-validate library.
"""
from __future__ import print_function
import yaml
import kubernetes_validate
import traceback
from pathlib import Path
from typing import Dict, Any
import os   


def validate_kubernetes_manifest(file_path: Path) -> Dict[str, Any]:
    """
    Validate a Kubernetes manifest file.
    
    Args:
        file_path: Path to the Kubernetes manifest file
        
    Returns:
        Dict containing validation results with structure:
        {
            'success': bool,
            'summary': {
                'valid': bool,    # Whether validation was successful
                'errors': int      # Number of validation errors
            },
            'errors': [
                {
                    'resource': str,      # Resource identifier
                    'message': str,       # Error message
                    'path': str,          # Path to the file
                    'type': str           # Error type
                },
                ...
            ]
        }
    """
    result = {
        "success": True,
        "summary": {"valid": True, "errors": 0},
        "errors": []
    }
        
   
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            manifests = list(yaml.safe_load_all(f))
        
        # Filter out None/empty documents
        manifests = [m for m in manifests if m is not None]
        if not manifests:
            raise ValueError("No valid YAML documents found in the file")
        
        # Process each manifest in the file
        for manifest in manifests:
            try:
                k8s_version = os.getenv("K8S_VERSION")
                kubernetes_validate.validate(manifest, k8s_version, strict=True)
                
            except kubernetes_validate.ValidationError as e:
                result["success"] = False
                result["summary"]["valid"] = False
                result["summary"]["errors"] += 1

                # Get resource context
                resource_kind = manifest.get('kind', 'Unknown')
                resource_name = manifest.get('metadata', {}).get('name', 'unknown')

                # Build detailed error info
                error_details = {
                    "type": "ValidationError",
                    "message": f"{'.'.join(map(str, getattr(e, 'path', [])))}: {getattr(e, 'message', str(e))}",
                    "resource": f"{resource_kind}/{resource_name}",
                    "error_type": type(e).__name__,

                }
                if hasattr(e, "schema_path"):
                    # Convert deque to list to ensure JSON serializability
                    error_details["schema_path"] = list(e.schema_path)

                result["errors"].append(error_details)

                
            except kubernetes_validate.SchemaNotFoundError as e:
                result["success"] = False
                result["summary"]["valid"] = False
                result["summary"]["errors"] += 1
                result["errors"].append({
                    "type": "SchemaError",
                    "message": f"Schema not found for version {k8s_version}. {str(e)}. Probably the definition of the apiVersion is not correct. Please check the apiVersion of the manifest.",
                    "resource": f"{manifest.get('kind', 'Unknown')}/{manifest.get('metadata', {}).get('name', 'unknown')}"
                })
                
    except yaml.YAMLError as e:
        result["success"] = False
        result["summary"]["valid"] = False
        result["summary"]["errors"] = 1
        result["errors"].append({
            "type": "YAMLError",
            "message": f"Invalid YAML: {str(e)}",
            "resource": "Unknown"
        })
        
    except Exception as e:
        result["success"] = False
        result["summary"]["valid"] = False
        result["summary"]["errors"] = 1
        result["errors"].append({
            "type": type(e).__name__,
            "message": f"Unexpected error: {str(e)}",
            "resource": "Unknown"
        })
    
    return result
