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
    Run Checkov scan on a file or directory.
    
    Args:
        file_path: Path to the file or directory to scan
        framework: Framework to use for scanning ('kubernetes' or 'dockerfile')
        skip_checks: List of check IDs to skip during scanning
    
    Returns:
        Dict containing scan results with structure:
        {
            'success': bool,
            'summary': {
                'valid': bool,
                'errors': int,
                'passed_checks': int,
                'failed_checks': int,
                'skipped_checks': int,
                'parsing_errors': int
            },
            'checks': {
                'passed': List[dict],
                'failed': List[dict],
                'skipped': List[dict]
            },
            'errors': List[dict]  # Only present if there was an error
        }
    """
    # Initialize result structure
    result = {
        "success": False,
        "summary": {
            "valid": False,
            "errors": 1,
            "passed_checks": 0,
            "failed_checks": 0,
            "skipped_checks": 0,
            "parsing_errors": 0
        },
        "checks": {
            "passed": [],
            "failed": [],
            "skipped": []
        },
        "errors": []
    }
    
    # Validate framework
    if framework not in ["kubernetes", "dockerfile"]:
        result["errors"].append({
            "type": "ValueError",
            "message": f"Unsupported framework: {framework}. Must be 'kubernetes' or 'dockerfile'.",
            "path": str(file_path)
        })
        return result
    
    # Import Checkov with proper error handling
    try:
        checkov = import_checkov()
        Runner = checkov['K8sRunner'] if framework == "kubernetes" else checkov['DockerfileRunner']
        parse = checkov['k8s_parse'] if framework == "kubernetes" else checkov['dockerfile_parse']
    except Exception as e:
        result["errors"].append({
            "type": type(e).__name__,
            "message": str(e),
            "path": str(file_path)
        })
        return result
    
    # Save original state
    original_argv = sys.argv.copy()
    original_dir = os.getcwd()
    
    try:
        # Change to the directory of the file being scanned
        file_dir = os.path.dirname(os.path.abspath(file_path))
        os.chdir(file_dir)
        file_name = os.path.basename(file_path)
        
        # Try to parse the file with Checkov's parser
        try:
            parse(str(file_path))
        except Exception as e:
            result["errors"].append({
                "type": "ParseError",
                "message": f"Failed to parse {framework} file: {str(e)}",
                "path": str(file_path)
            })
            result["summary"]["parsing_errors"] = 1
            return result
        
        # Create Checkov runner with appropriate framework
        runner = Runner()
        runner.templateRendererCommand = "noop"
        runner.templateRendererCommandOptions = ""
        runner.skip_invalid = True
        
        # Set up runner filter with skip checks if provided
        runner_filter_kwargs = {'show_progress_bar': False}
        if skip_checks:
            runner_filter_kwargs['skip_checks'] = skip_checks
            
        runner.runner_filter = checkov['RunnerFilter'](**runner_filter_kwargs)
        
        # Run the scan
        report = runner.run(root_folder=file_dir, files=[file_name], runner_filter=runner.runner_filter)
        
        if not report or not isinstance(report, checkov['Report']):
            result["errors"].append({
                "type": "CheckovError",
                "message": "Checkov scan did not produce any results",
                "path": str(file_path)
            })
            return result
            
        # Process the checks
        def process_checks(checks):
            """Convert Checkov checks to a serializable format."""
            processed = []
            for check in checks:
                try:
                    check_dict = {
                        'check_id': getattr(check, 'check_id', ''),
                        'check_name': getattr(check, 'check_name', ''),
                        'resource': getattr(check, 'resource', ''),
                        'file_path': getattr(check, 'file_path', ''),
                        'file_line_range': list(getattr(check, 'file_line_range', [])),
                        'severity': getattr(check, 'severity', ''),
                        'guideline': getattr(check, 'guideline', '')
                    }
                    processed.append({k: v for k, v in check_dict.items() if v})
                except Exception as e:
                    print(f"Error processing check: {e}", file=sys.stderr)
            return processed
        
        # Process only failed checks with all available details
        def process_failed_checks(checks):
            """Convert failed checks to a detailed serializable format."""
            if not checks:
                return []
                
            processed = []
            for check in checks:
                if not check:
                    continue
                    
                try:
                    # Safely get attributes with proper defaults
                    check_dict = {}
                    
                    # Basic check info
                    check_dict['check_id'] = getattr(check, 'check_id', '')
                    check_dict['check_name'] = getattr(check, 'check_name', '')
                    check_dict['severity'] = getattr(check, 'severity', 'UNKNOWN')
                    check_dict['guideline'] = getattr(check, 'guideline', '')
                    
                    # Resource info
                    check_dict['resource'] = getattr(check, 'resource', '')
                    check_dict['resource_address'] = getattr(check, 'resource_address', '')
                    
                    # File location (only include relative path)
                    check_dict['file_path'] = getattr(check, 'file_path', '')
                    
                    # Line numbers
                    line_range = getattr(check, 'file_line_range', None)
                    check_dict['file_line_range'] = list(line_range) if line_range else []
                    
                    # Additional details
                    check_dict['id'] = getattr(check, 'id', '')
                    check_dict['check_class'] = getattr(check, 'check_class', '')
                    
                    # Handle potentially None values for collections
                    evaluated_keys = getattr(check, 'evaluated_keys', None)
                    check_dict['evaluated_keys'] = list(evaluated_keys) if evaluated_keys else []
                    
                    entity_tags = getattr(check, 'entity_tags', None)
                    check_dict['entity_tags'] = dict(entity_tags) if entity_tags else {}
                    
                    details = getattr(check, 'details', None)
                    check_dict['details'] = list(details) if details else []
                    
                    # Add any additional attributes that might be useful (excluding specific fields)
                    excluded_attrs = {
                        'code_block',
                        'file_abs_path',
                        'repo_file_path',
                        *check_dict.keys()  # Skip already processed attributes
                    }
                    
                    for attr in dir(check):
                        if (not attr.startswith('_') and 
                            attr not in excluded_attrs and
                            not callable(getattr(check, attr, None))):
                            try:
                                val = getattr(check, attr, None)
                                if val is not None:
                                    check_dict[attr] = val
                            except Exception:
                                continue
                    
                    # Only add non-empty values
                    processed.append({
                        k: v for k, v in check_dict.items() 
                        if (v is not None and v != '' and v != [] and v != {})
                    })
                    
                except Exception as e:
                    error_msg = f"Error processing check {getattr(check, 'check_id', 'unknown')}: {str(e)}"
                    print(error_msg, file=sys.stderr)
                    # Include the error in the results
                    processed.append({
                        'error': traceback.format_exc(),
                        'check_id': getattr(check, 'check_id', 'unknown'),
                        'message': 'Failed to process this check'
                    })
                    
            return processed
        
        # Process checks
        failed_checks = process_failed_checks(report.failed_checks)
        
        # Count all checks (passed, failed, skipped)
        passed_count = len(report.passed_checks) if hasattr(report, 'passed_checks') else 0
        failed_count = len(failed_checks)
        skipped_count = len(report.skipped_checks) if hasattr(report, 'skipped_checks') else 0
        parsing_errors = len(report.parsing_errors) if hasattr(report, 'parsing_errors') else 0
        
        # Update result with only failed checks details
        result["checks"]["failed"] = failed_checks
        
        # Update summary with all counts
        result["summary"].update({
            "passed_checks": passed_count,
            "failed_checks": failed_count,
            "skipped_checks": skipped_count,
            "parsing_errors": parsing_errors,
            "total_checks": passed_count + failed_count + skipped_count
        })
        
        # Set success and valid based on results
        result["success"] = len(failed_checks) == 0 and result["summary"]["parsing_errors"] == 0
        result["summary"]["valid"] = result["success"]
        result["summary"]["errors"] = 0 if result["success"] else 1
        
        return result
            
    except Exception as e:
        # Handle any unexpected errors
        result["errors"].append({
            "type": type(e).__name__,
            "message": f"Unexpected error during {framework} validation: {traceback.format_exc()}",
            "path": str(file_path)
        })
        result["summary"]["errors"] = 1
        return result
        
    finally:
        # Restore original state
        sys.argv = original_argv
        os.chdir(original_dir)
    
    return result
