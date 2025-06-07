"""
The config_validator tool validates configuration files including Kubernetes manifests, Docker Compose files,
and other YAML/JSON configuration files. Uses various validation backends including
Checkov for security scanning.
"""
import os

from pathlib import Path
from typing import Dict, Any, Literal, Optional, List
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

# Import validators
from src.crewai.tools.utils.yaml_validator import validate_yaml_file
from src.crewai.tools.utils.kubernetes_validator import validate_kubernetes_manifest
from src.crewai.tools.utils.docker_validator import validate_docker_compose
from src.crewai.tools.utils.checkov_validator import run_checkov_scan
from src.crewai.tools.utils.docker_dry_run import docker_dry_run
from src.crewai.tools.utils.k8s_dry_run import k8s_dry_run

class ValidationRequest(BaseModel):
    """Request model for the config validator tool."""
    file_path: str = Field(
        ...,
        description="Path to the file to validate, relative to the base directory"
    )
    file_type: Literal["kubernetes", "docker", "yaml"] = Field(
        ...,
        description="Type of configuration file to validate"
    )
    enable_security_scan: bool = Field(
        default=True,
        description="Whether to run security scanning with Checkov"
    )
    skip_checks: Optional[List[str]] = Field(
        default_factory=list,
        description="List of check IDs to skip during validation"
    )

class ConfigValidatorTool(BaseTool):
    """
    The config_validator tool validates configuration files including Kubernetes manifests, Docker Compose files,
    and other YAML configuration files.
    
    Parameters:
        base_dir (str | Path): The base directory for all file operations.
    """
    name: str = "config_validator"
    description: str = (
        "The config_validator tool validates configuration files including Kubernetes manifests, Docker Compose files, "
        "and other YAML configuration files. Returns a detailed validation report."
    )
    args_schema: type[BaseModel] = ValidationRequest
    _base_dir: Path = None

    def __init__(self, base_dir: str | Path, **kwargs) -> None:
        """Initialize the ConfigValidatorTool."""
        super().__init__(**kwargs)
        self._base_dir = Path(base_dir)

    def _run(
        self,
        file_path: str,
        file_type: str,
        enable_security_scan: bool = True,
        skip_checks: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate a configuration file.
        
        Args:
            file_path: Path to the file to validate, relative to the base directory
            file_type: Type of configuration file ('kubernetes', 'docker')
            enable_security_scan: Whether to run security scanning with Checkov
            skip_checks: List of check IDs to skip during validation
            
        Returns:
            Dict containing validation results with the following structure:
            {
                "file_path": str,
                "file_type": str,
                "valid": bool,
                "summary": {
                    "passed_checks": int,
                    "failed_checks": int,
                    "skipped_checks": int,
                    "parsing_errors": int,
                    "total_checks": int,
                    "valid": bool
                },
                "validations": {
                    "yaml": { ... },
                    "kubernetes|docker": { ... },
                    "security_scan": { ... }
                },
                "errors": List[Dict[str, str]]
            }
        """
        skip_checks = skip_checks or []
        errors: List[Dict[str, str]] = []
        
        # Initialize result with empty validations
        result: Dict[str, Any] = {
            "file_path": str(file_path),
            "file_type": file_type,
            "valid": True,
            "validations": {}
            # No summary field - it's redundant with other information
        }
        
        try:
            # Convert path separators to be OS-agnostic
            normalized_path = file_path.replace("/", os.path.sep)
            full_path = Path(str(self._base_dir)) / normalized_path
            
            # 1. Basic YAML validation (now with multi-document support)
            try:
                yaml_result = validate_yaml_file(full_path)
                result["validations"]["yaml"] = yaml_result
                
                # Extract document count information and add to main result
                doc_count = yaml_result.get("summary", {}).get("doc_count", 0)
                if doc_count > 0:
                    result["document_count"] = doc_count
                    if doc_count > 1:
                        result["multi_document"] = True
                        valid_docs = sum(1 for d in yaml_result.get("documents", []) if d.get("valid", False))
                        result["valid_documents"] = valid_docs
                
                # Update validation result status
                if not yaml_result.get("success", True):
                    result["valid"] = False
                
                # Document count info was already added above
                    
            except Exception as e:
                yaml_result = {
                    "valid": False,
                    "doc_count": 0,
                    "documents": [],
                    "errors": [{
                        "type": "Error",
                        "message": f"YAML validation failed: {str(e)}",
                        "doc_index": 0
                    }]
                }
                
                result["validations"]["yaml"] = yaml_result
                result["valid"] = False
                return result
            
            # 2. Type-specific validation
            type_specific_result = None
            validation_type = file_type.capitalize()
            
            try:
                if file_type == "kubernetes":
                    type_specific_result = validate_kubernetes_manifest(full_path)
                elif file_type == "docker":
                    type_specific_result = validate_docker_compose(full_path)
                
                if type_specific_result:
                    result["validations"][file_type] = type_specific_result
                    # Set validation status directly without using summary
                    if not type_specific_result.get("success", True):
                        result["valid"] = False
                        
            except Exception as e:
                type_specific_result = {
                    "success": False,
                    "error": f"{validation_type} validation failed: {str(e)}",
                    "details": {"exception": str(e)},
                    "summary": {
                        "valid": False,
                        "passed_checks": 0,
                        "failed_checks": 1,
                        "parsing_errors": 1,
                        "total_checks": 1
                    }
                }
                result["validations"][file_type] = type_specific_result
                result["valid"] = False
            
            # 2.5. Dry run validations
            if file_type == "kubernetes":
                dry_run_result = k8s_dry_run(full_path)
                result["validations"]["kubernetes_dry_run"] = {
                    "valid": dry_run_result["success"],
                    "errors": dry_run_result.get("error", ""),
                }
                if not dry_run_result["success"]:
                    result["valid"] = False
            elif file_type == "docker":
                dry_run_result = docker_dry_run(full_path)
                result["validations"]["docker_dry_run"] = {
                    "valid": dry_run_result["success"],
                    "errors": dry_run_result.get("error", "")
                }
                if not dry_run_result["success"]:
                    result["valid"] = False

            # 3. Security scanning with Checkov if enabled
            if enable_security_scan and file_type in ["kubernetes", "docker"]:
                try:
                    checkov_result = run_checkov_scan(
                        full_path,
                        framework=file_type,
                        skip_checks=skip_checks
                    )
                    result["validations"]["security_scan"] = checkov_result
                    # Set validation status directly without using summary
                    if not checkov_result.get("success", True):
                        result["valid"] = False
                    
                except Exception as e:
                    checkov_result = {
                        "valid": False,
                        "errors": f"Security scan failed: {str(e)}",
                        "passed_checks": 0,
                        "failed_checks": 1,
                        "parsing_errors": 1,
                        "total_checks": 1,
                        "failed_checks_list": [],
                        "skipped_checks_list": []
                    }
                    result["validations"]["security_scan"] = checkov_result
                    result["valid"] = False
                    
            # No need for summary-based final update
            
            return result
            
        except Exception as e:
            # Handle unexpected errors
            result["valid"] = False
            error_info = {
                "valid": False,
                "errors": f"Unexpected error during validation: {str(e)}",
            }
            result["validations"]["general"] = error_info
            # No top-level errors as requested
            return result
    
    # _update_validation_result method removed - summary data and error aggregation is redundant
