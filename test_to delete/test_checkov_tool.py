"""
Checkov JSON Reporter for Kubernetes manifests.
Provides a clean JSON output of Checkov scan results.
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

def validate_yaml(file_path: str) -> Tuple[bool, str]:
    """Validate YAML file and return (is_valid, error_message) tuple."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        return True, ""
    except yaml.YAMLError as e:
        return False, f"Invalid YAML: {str(e)}"
    except Exception as e:
        return False, f"Error reading file: {str(e)}"

@dataclass
class CheckovResult:
    """Structured result of a Checkov scan."""
    success: bool
    summary: Dict[str, Any]
    passed_checks: List[Dict[str, Any]]
    failed_checks: List[Dict[str, Any]]
    skipped_checks: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "summary": self.summary,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "skipped_checks": self.skipped_checks
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

def scan_kubernetes_manifest(file_path: str, skip_checks: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run Checkov on a Kubernetes manifest file and return results as JSON.
    
    Args:
        file_path: Path to the Kubernetes manifest file
        skip_checks: Optional list of check IDs to skip
        
    Returns:
        Dict containing scan results in a clean JSON-serializable format with structure:
        {
            'success': bool,
            'summary': dict,
            'passed_checks': list,
            'failed_checks': list,
            'skipped_checks': list,
            'error': str  # Only present if there was an error
        }
    """
    # Initialize result structure
    empty_result = {
        'success': False,
        'summary': {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'parsing_errors': 0,
            'resource_count': 0
        },
        'passed_checks': [],
        'failed_checks': [],
        'skipped_checks': []
    }
    
    if not os.path.isfile(file_path):
        empty_result['error'] = f"File not found: {file_path}"
        return empty_result
    
    # Validate YAML first
    is_valid, error = validate_yaml(file_path)
    if not is_valid:
        empty_result['error'] = error
        empty_result['summary']['parsing_errors'] = 1
        return empty_result
    
    # Save original arguments and working directory
    original_argv = sys.argv.copy()
    original_dir = os.getcwd()
    
    try:
        # Change to the directory of the file being scanned
        file_dir = os.path.dirname(os.path.abspath(file_path))
        os.chdir(file_dir)
        file_name = os.path.basename(file_path)
        
        # Import Checkov here to avoid loading it unless needed
        from checkov.runner_filter import RunnerFilter
        from checkov.kubernetes.runner import Runner as K8sRunner
        from checkov.common.output.report import Report
        from checkov.kubernetes.parser.parser import parse
        
        # Try to parse the file with Checkov's parser
        try:
            parse(file_path)
        except Exception as e:
            empty_result['error'] = f"Failed to parse Kubernetes manifest: {str(e)}"
            empty_result['summary']['parsing_errors'] = 1
            return empty_result
        
        # Configure and run the runner directly
        runner = K8sRunner()
        runner_filter = RunnerFilter(skip_checks=skip_checks)
        
        # Run the scan
        report = runner.run(root_folder=file_dir, files=[file_name], runner_filter=runner_filter)
        
        if not report or not isinstance(report, Report):
            empty_result['error'] = "Checkov scan did not produce any results"
            return empty_result
            
        # Check for parsing errors in the report
        if hasattr(report, 'parsing_errors') and report.parsing_errors:
            empty_result['error'] = f"Found {len(report.parsing_errors)} parsing errors in the manifest"
            empty_result['summary']['parsing_errors'] = len(report.parsing_errors)
            return empty_result
        
        def process_checks(checks):
            """Convert Checkov checks to a serializable format."""
            result = []
            for check in checks:
                try:
                    check_dict = {
                        'check_id': getattr(check, 'check_id', ''),
                        'check_name': getattr(check, 'check_name', ''),
                        'check_result': getattr(check, 'check_result', {}),
                        'file_path': getattr(check, 'file_path', ''),
                        'file_line_range': list(getattr(check, 'file_line_range', [])),
                        'resource': getattr(check, 'resource', ''),
                        'evaluations': getattr(check, 'evaluations', None),
                        'code_block': list(getattr(check, 'code_block', [])),
                    }
                    result.append({k: v for k, v in check_dict.items() if v is not None})
                except Exception as e:
                    print(f"Error processing check: {e}", file=sys.stderr)
            return result
        
        # Only include failed checks in the results
        failed_checks = process_checks(report.failed_checks)
        passed_count = len(report.passed_checks)
        skipped_count = len(report.skipped_checks) if hasattr(report, 'skipped_checks') else 0
        
        # Build the result object with only failed checks
        result = {
            'success': len(failed_checks) == 0,
            'summary': {
                'passed': passed_count,
                'failed': len(failed_checks),
                'skipped': skipped_count,
                'parsing_errors': len(report.parsing_errors) if hasattr(report, 'parsing_errors') else 0,
                'resource_count': len(report.resources) if hasattr(report, 'resources') else 0,
            },
            'failed_checks': failed_checks
        }
        
        # Only include the summary fields if there are passed or skipped checks
        if passed_count > 0 or skipped_count > 0:
            result['summary_info'] = {
                'passed_checks_count': passed_count,
                'skipped_checks_count': skipped_count
            }
            
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "summary": {},
            "passed_checks": [],
            "failed_checks": [],
            "skipped_checks": []
        }
    finally:
        # Restore original state
        sys.argv = original_argv
        os.chdir(original_dir)

if __name__ == "__main__":


  result = scan_kubernetes_manifest(
      "temp/deployment.yaml"
  )

  pprint.pprint(result)
  

  # Command line usage
  # python test_checkov_tool.py path/to/manifest.yaml --skip CKV_K8S_1 CKV_K8S_2