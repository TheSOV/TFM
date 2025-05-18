"""
Kubernetes Manifest Validator

Provides validation for Kubernetes manifest files using the kubernetes-validate library.
"""
import os
import sys
import json
import yaml
import warnings
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import pprint

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=SyntaxWarning)


@dataclass
class KubernetesValidationResult:
    """Structured result of a Kubernetes manifest validation."""
    success: bool
    summary: Dict[str, int]
    errors: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "summary": self.summary,
            "errors": [dict(e) for e in self.errors] if self.errors else []
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

def validate_kubernetes_manifest(file_path: str, k8s_version: str = "1.25.0") -> Dict[str, Any]:
    """
    Validate a Kubernetes manifest file using kubernetes-validate.
    
    Args:
        file_path: Path to the Kubernetes manifest file
        k8s_version: Kubernetes version to validate against (default: 1.25.0)
        
    Returns:
        Dict containing validation results with structure:
        {
            'success': bool,
            'summary': {
                'valid': int,     # Number of valid resources
                'invalid': int,   # Number of invalid resources
                'errors': int     # Number of validation errors
            },
            'errors': [
                {
                    'resource': str,      # Resource identifier
                    'message': str,       # Error message
                    'path': List[str],    # Path to the error in the manifest
                    'validator': str      # Validator that failed
                },
                ...
            ]
        }
    """
    # Initialize result structure
    empty_result = {
        'success': False,
        'summary': {
            'valid': 0,
            'invalid': 0,
            'errors': 0
        },
        'errors': []
    }
    
    if not os.path.isfile(file_path):
        empty_result['error'] = f"File not found: {file_path}"
        return empty_result
    
    # ---
    # Direct use of the kubernetes-validate Python package (NOT the CLI tool)
    # This is the recommended and programmatic way to validate manifests in Python.
    # ---
    try:
        import kubernetes_validate  # Python package, not CLI
        from kubernetes_validate import ValidationError
    except ImportError:
        empty_result['error'] = (
            "kubernetes-validate library not installed. Please install it with: pip install kubernetes-validate"
        )
        return empty_result

    try:
        # Read the YAML file as Python objects
        with open(file_path, 'r', encoding='utf-8') as f:
            manifests = list(yaml.safe_load_all(f))
        # Filter out None/empty documents
        manifests = [m for m in manifests if m is not None]
        if not manifests:
            empty_result['error'] = "No valid YAML documents found in the file"
            return empty_result
        results = []
        for manifest in manifests:
            try:
                # Validate using the Python API (not shell/CLI)
                # This will raise ValidationError if the manifest is invalid
                kubernetes_validate.validate(manifest, k8s_version, strict=True)
                results.append({'valid': True, 'manifest': manifest})
            except ValidationError as e:
                error_details = []
                for error in e.errors:
                    error_details.append({
                        'resource': f"{manifest.get('kind', 'Unknown')}/{manifest.get('metadata', {}).get('name', 'unknown')}",
                        'message': str(error),
                        'path': getattr(error, 'path', []),
                        'validator': getattr(error, 'validator', 'unknown')
                    })
                results.append({
                    'valid': False,
                    'manifest': manifest,
                    'errors': error_details
                })
        # Count valid/invalid results
        valid_count = sum(1 for r in results if r['valid'])
        invalid_count = len(results) - valid_count
        error_count = sum(len(r.get('errors', [])) for r in results if not r['valid'])
        # Get all errors
        all_errors = []
        for result in results:
            if not result['valid']:
                all_errors.extend(result['errors'])
        return {
            'success': invalid_count == 0,
            'summary': {
                'valid': valid_count,
                'invalid': invalid_count,
                'errors': error_count
            },
            'errors': all_errors
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': f"Validation failed: {str(e)}",
            'summary': empty_result['summary'],
            'errors': [{'message': str(e)}]
        }


if __name__ == "__main__":
    result = validate_kubernetes_manifest("temp/deployment.yaml")
    pprint.pprint(result)
    