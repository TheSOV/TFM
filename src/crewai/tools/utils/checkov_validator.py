"""
Checkov Validator

Provides security and compliance validation for infrastructure as code files
using Checkov.
"""
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

def import_checkov():
    """Import Checkov modules with proper error handling."""
    try:
        from checkov.runner_filter import RunnerFilter
        from checkov.kubernetes.runner import Runner as K8sRunner
        from checkov.dockerfile.runner import Runner as DockerfileRunner
        from checkov.common.output.report import Report
        from checkov.kubernetes.parser.parser import parse as k8s_parse
        from checkov.dockerfile.parser import parse as dockerfile_parse
        
        return {
            'RunnerFilter': RunnerFilter,
            'K8sRunner': K8sRunner,
            'DockerfileRunner': DockerfileRunner,
            'Report': Report,
            'k8s_parse': k8s_parse,
            'dockerfile_parse': dockerfile_parse
        }
    except ImportError as e:
        raise ImportError("Checkov is not installed. Please install it with: pip install checkov") from e
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Checkov: {str(e)}") from e

def run_checkov_scan(
    file_path: Path,
    framework: str = "kubernetes",
    skip_checks: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Run Checkov scan on a file, ensuring it only scans the specified file.
    This is done by changing the current working directory to the file's parent
    directory to constrain Checkov's discovery process.
    """
    skip_checks = skip_checks or []
    result = {
        "success": False,
        "summary": {"valid": False, "errors": 1, "passed_checks": 0, "failed_checks": 0, "skipped_checks": 0, "parsing_errors": 0},
        "checks": {"failed": []},
        "errors": []
    }

    # The framework name for Docker in Checkov is 'dockerfile'
    if framework == "docker":
        framework = "dockerfile"

    if framework not in ["kubernetes", "dockerfile"]:
        result["errors"].append({"type": "ValueError", "message": f"Unsupported framework for Checkov: {framework}."})
        return result

    original_cwd = Path.cwd()
    # Ensure the target directory exists before trying to change to it
    target_dir = file_path.parent.resolve()
    if not target_dir.is_dir():
        result["errors"].append({"type": "DirectoryNotFoundError", "message": f"The parent directory of the file to be scanned does not exist: {target_dir}"})
        return result

    try:
        checkov = import_checkov()
        Runner = checkov['K8sRunner'] if framework == "kubernetes" else checkov['DockerfileRunner']
        runner = Runner()
        runner_filter = checkov['RunnerFilter'](framework=framework, skip_checks=skip_checks)

        # Change to the file's directory to constrain the scan
        os.chdir(target_dir)

        # Run the scan on the specific file from the new CWD
        report = runner.run(
            root_folder=None,  # Scan from the current directory
            files=[file_path.name],  # Scan only the target file relative to the new CWD
            runner_filter=runner_filter
        )

        # Process the report
        summary = report.get_summary()
        result["summary"] = {
            "valid": summary.get("passed", 0) > 0 and summary.get("failed", 0) == 0,
            "passed_checks": summary.get("passed", 0),
            "failed_checks": summary.get("failed", 0),
            "skipped_checks": summary.get("skipped", 0),
            "parsing_errors": summary.get("parsing_errors", 0),
        }
        
        def _record_to_dict(record):
            # Extract only the necessary fields for a concise report
            return {
                "check_id": record.check_id,
                "check_name": record.check_name,
                "check_status": record.check_result.get('result'),
                "resource": record.resource,
                "file_path": record.file_path,
                "file_line_range": record.file_line_range,
            }

        # Only include failed checks in the final report for conciseness
        result["checks"]["failed"] = [_record_to_dict(check) for check in report.failed_checks]
        
        if report.parsing_errors:
            result["errors"].append({"type": "ParsingError", "message": f"{len(report.parsing_errors)} parsing errors found."})

        result["success"] = not report.failed_checks and not report.parsing_errors

    except Exception as e:
        result["errors"].append({
            "type": "ExecutionError",
            "message": f"Checkov scan failed: {str(e)}",
            "trace": traceback.format_exc()
        })
    finally:
        # Always restore the original working directory
        os.chdir(original_cwd)

    return result
   