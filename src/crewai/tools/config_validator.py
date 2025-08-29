"""
The config_validator tool validates configuration files including Kubernetes manifests, Docker Compose files,
and other YAML/JSON configuration files. Uses various validation backends including
Checkov for security scanning.
"""
import os
import time
import logging
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

_logger = logging.getLogger(__name__)

class ValidationRequest(BaseModel):
    """Request model for the config validator tool."""
    enable_security_scan: bool = Field(
        default=True,
        description="Whether to run security scanning with Checkov"
    )
    skip_checks: Optional[List[str]] = Field(
        default=None,
        description="List of check IDs to skip during validation. If not provided, defaults to skipping [\"CKV_K8S_40\"]."
    )

class ConfigValidatorTool(BaseTool):
    """
    The config_validator tool validates configuration files including Kubernetes manifests, Docker Compose files,
    and other YAML configuration files.
    
    Parameters:
        file_path (str | Path): The full path to the configuration file to validate.
    """
    name: str = "config_validator"
    description: str = (
        "The config_validator tool validates Kubernetes manifest files. "
        "Returns a detailed validation report including syntax, schema, and security checks."
    )
    args_schema: type[BaseModel] = ValidationRequest
    _file_path: Path = None

    def __init__(self, file_path: str | Path, **kwargs) -> None:
        """
        Initialize the ConfigValidatorTool with an absolute file path.
        Args:
            file_path (str | Path): Path to the configuration file (relative, absolute, or with ~).
            **kwargs: Additional keyword arguments for BaseTool.
        """
        super().__init__(**kwargs)
        self._file_path = Path(file_path).expanduser().resolve()
        self.description = f"Validates the configuration file at {self._file_path}."

    def _run(
        self,
        enable_security_scan: bool = True,
        skip_checks: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        file_type = "kubernetes"
        if skip_checks is None or skip_checks == []:
            # If the agent does not provide a list, default to skipping CKV_K8S_40.
            # If an empty list is provided, no checks will be skipped.
            skip_checks = ["CKV_K8S_40"]
        
        result: Dict[str, Any] = {
            "file_path": str(self._file_path),
            "file_type": file_type,
            "valid": True,
            "validations": {}
        }

        # 1. File Existence Check
        if not self._file_path.exists():
            _logger.error(f"File not found: {self._file_path}")
            result["valid"] = False
            result["validations"]["file_existence"] = {
                "success": False,
                "message": f"File not found at path: {self._file_path}"
            }
            return result

        # 2. YAML Validation
        try:
            yaml_result = validate_yaml_file(self._file_path)
            if not yaml_result.get("success", True):
                result["valid"] = False
                result["validations"]["yaml"] = yaml_result
        except Exception as e:
            _logger.error(f"An exception occurred during YAML validation: {e}", exc_info=True)
            result["valid"] = False
            result["validations"]["yaml"] = {"success": False, "error": str(e)}
            return result # Stop if YAML is invalid

        # 3. Duplicate Resource Detection
        doc_count = yaml_result.get("summary", {}).get("doc_count", 0)
        if doc_count > 1:
            # Use a dictionary to track all indices for each resource
            seen_resources = {}
            for idx, doc_info in enumerate(yaml_result.get("documents", [])):
                doc = doc_info.get("doc")
                if isinstance(doc, dict) and all(k in doc for k in ["apiVersion", "kind", "metadata"]):
                    resource_key = (
                        doc.get("apiVersion"),
                        doc.get("kind"),
                        doc.get("metadata", {}).get("name"),
                        doc.get("metadata", {}).get("namespace")
                    )
                    if resource_key not in seen_resources:
                        seen_resources[resource_key] = []
                    seen_resources[resource_key].append(idx)
            
            # Filter for resources that appeared more than once
            duplicates = []
            for resource_key, indices in seen_resources.items():
                if len(indices) > 1:
                    duplicates.append({
                        "kind": resource_key[1],
                        "name": resource_key[2],
                        "namespace": resource_key[3],
                        "indices": sorted(indices)  # Return sorted 0-based indices
                    })

            if duplicates:
                result["valid"] = False
                result["validations"]["duplicate_check"] = {
                    "success": False,
                    "duplicates": duplicates
                }

        # 4. Kubernetes Manifest and Dry-Run Validation
        try:
            k8s_result = validate_kubernetes_manifest(self._file_path)
            if not k8s_result.get("success", True):
                result["valid"] = False
                result["validations"]["kubernetes_schema"] = k8s_result

            dry_run_result = k8s_dry_run(self._file_path)
            if not dry_run_result["success"]:
                result["valid"] = False
                result["validations"]["kubernetes_dry_run"] = dry_run_result

        except Exception as e:
            _logger.error(f"An exception occurred during Kubernetes validation: {e}", exc_info=True)
            result["valid"] = False
            result["validations"]["kubernetes"] = {"success": False, "error": str(e)}

        # 5. Security Scanning
        if enable_security_scan:
            try:
                checkov_result = run_checkov_scan(self._file_path, framework=file_type, skip_checks=skip_checks)
                if not checkov_result.get("success", True):
                    result["valid"] = False
                    result["validations"]["security_scan"] = checkov_result
            except Exception as e:
                _logger.error(f"An exception occurred during security scan: {e}", exc_info=True)
                result["valid"] = False
                result["validations"]["security_scan"] = {"success": False, "error": str(e)}

        return result
    
    # _update_validation_result method removed - summary data and error aggregation is redundant
