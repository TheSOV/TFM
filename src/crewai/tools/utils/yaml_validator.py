"""
YAML Validation Utilities

Provides functions to validate YAML files and content.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
import yaml
import io
from yamllint import linter
from yamllint.config import YamlLintConfig

def run_yamllint(content: str, config_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Run yamllint on YAML content to find issues like duplicate keys.
    
    Args:
        content (str): YAML content as string
        config_path (Optional[str]): Path to a yamllint configuration file
        
    Returns:
        List[Dict[str, Any]]: List of validation issues found by yamllint
    """
    # Create a custom configuration that disables indentation and line-length rules
    config_str = '''
    extends: default
    rules:
      key-duplicates: enable
      line-length: disable
      indentation: disable
      trailing-spaces: disable
      document-start: disable
      braces: disable
      brackets: disable
      comments: disable
      comments-indentation: disable
      document-end: disable
      empty-lines: disable
      empty-values: disable
      hyphens: disable
      key-ordering: disable
      new-line-at-end-of-file: disable
      new-lines: disable
      quoted-strings: disable
    '''
    
    # If a config file is provided, merge it with our custom config
    if config_path:
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f) or {}
        
        # Ensure rules exist in user config
        if 'rules' not in user_config:
            user_config['rules'] = {}
            
        # Force disable the rules we want to ignore
        user_config['rules']['line-length'] = 'disable'
        user_config['rules']['indentation'] = 'disable'
        user_config['rules']['trailing-spaces'] = 'disable'
        user_config['rules']['document-start'] = 'disable'
        user_config['rules']['braces'] = 'disable'
        user_config['rules']['brackets'] = 'disable'
        user_config['rules']['comments'] = 'disable'
        user_config['rules']['comments-indentation'] = 'disable'
        user_config['rules']['document-end'] = 'disable'
        user_config['rules']['empty-lines'] = 'disable'
        user_config['rules']['empty-values'] = 'disable'
        user_config['rules']['hyphens'] = 'disable'
        user_config['rules']['key-ordering'] = 'disable'
        user_config['rules']['new-line-at-end-of-file'] = 'disable'
        user_config['rules']['new-lines'] = 'disable'
        user_config['rules']['quoted-strings'] = 'disable'
        
        # Convert back to string for YamlLintConfig
        config_str = yaml.safe_dump(user_config)
    
    conf = YamlLintConfig(content=config_str)
    
    # Run yamllint
    problems = linter.run(content, conf)
    
    # Convert problems to a more usable format
    issues = []
    for problem in problems:
        issues.append({
            "line": problem.line,
            "column": problem.column,
            "level": problem.level,  # 'error' or 'warning'
            "message": problem.message,
            "rule": problem.rule,    # e.g., 'key-duplicates'
            "desc": problem.desc     # More detailed description
        })
    
    return issues

def validate_yaml_file(file_path: Path) -> Dict[str, Any]:
    """
    Validate a YAML file, supporting multiple YAML documents in a single file.
    
    Args:
        file_path (Path): Path to the YAML file to validate
        
    Returns:
        Dict[str, Any]: Validation results with the following structure:
        {
            'success': bool,          # Overall success status
            'summary': {
                'valid': bool,        # True if all YAML documents are valid
                'errors': int,        # Number of errors found
                'doc_count': int      # Number of YAML documents found
            },
            'documents': [            # List of validation results for each document
                {
                    'index': int,     # Document index (0-based)
                    'valid': bool,    # Validation status for this document
                    'error': str      # Error message if invalid (None if valid)
                }
            ],
            'errors': [              # Detailed error information
                {
                    'type': str,      # Error type (e.g., 'YAMLError')
                    'message': str,   # Error message
                    'path': str,      # Path to the file
                    'doc_index': int  # Document index where error occurred
                }
            ]
        }
    """
    result = {
        "success": True,
        "summary": {"valid": True, "errors": 0, "doc_count": 0},
        "documents": [],
        "errors": []
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read the content once to get a string representation
            content = f.read()
            
            # If file is empty or contains only whitespace, return success with doc_count=0
            if not content.strip():
                return result
                
            # Run yamllint to check for issues like duplicate keys
            yamllint_issues = run_yamllint(content)
            
            # Process all YAML documents in the file
            docs = list(yaml.safe_load_all(content))
            result["summary"]["doc_count"] = len(docs)
            
            # Group yamllint issues by document
            doc_issues = {}
            for issue in yamllint_issues:
                # Determine which document this issue belongs to based on line number
                # This is approximate as yamllint doesn't provide doc index directly
                doc_index = 0
                line_count = 0
                for i, doc_content in enumerate(content.split('---')):
                    if i == 0 and not doc_content.strip():
                        continue  # Skip empty first document before first ---
                    line_count += doc_content.count('\n') + 1  # +1 for the '---' line itself
                    if issue["line"] <= line_count:
                        doc_index = i
                        break
                
                if doc_index not in doc_issues:
                    doc_issues[doc_index] = []
                doc_issues[doc_index].append(issue)
            
            # Validate each document individually
            for i, doc in enumerate(docs):
                if doc is None:  # Empty document (just '---')
                    result["documents"].append({
                        "index": i,
                        "valid": True,
                        "error": None
                    })
                    continue
                
                # Check if this document has issues
                if i in doc_issues and doc_issues[i]:
                    # Document has issues
                    issues = doc_issues[i]
                    # Get the first error or warning if available
                    error_issue = next((issue for issue in issues if issue["level"] == "error"), 
                                      next((issue for issue in issues), None))
                    
                    if error_issue:
                        error_msg = f"{error_issue['message']} ({error_issue['rule']}) at line {error_issue['line']}"
                        result["success"] = False
                        result["summary"]["valid"] = False
                        result["summary"]["errors"] += 1
                        
                        result["documents"].append({
                            "index": i,
                            "valid": False,
                            "error": error_msg
                        })
                        
                        # Add detailed error info for each issue in this document
                        for issue in issues:
                            # Create consistent error type format
                            if issue['rule'] == 'key-duplicates':
                                error_type = "DuplicateKeyError"
                            else:
                                error_type = f"YamlLint{issue['level'].capitalize()}"
                                
                            result["errors"].append({
                                "type": error_type,
                                "message": f"{issue['message']} ({issue['rule']}) at line {issue['line']}, column {issue['column']}",
                                "path": str(file_path),
                                "doc_index": i
                            })
                        continue
                
                # Document is valid
                result["documents"].append({
                    "index": i,
                    "valid": True,
                    "error": None
                })
            
        return result
        
    except yaml.YAMLError as e:
        result["success"] = False
        result["summary"]["valid"] = False
        result["summary"]["errors"] += 1
        doc_index = getattr(e, 'problem_mark', None)
        if doc_index:
            # Get the document index from the error's problem_mark if available
            doc_index = doc_index.index
        else:
            doc_index = 0
            
        error_msg = f"Invalid YAML: {str(e)}"
        
        # Add document-specific error info
        if len(result["documents"]) <= doc_index:
            # If we haven't processed this document yet, add it
            result["documents"].append({
                "index": doc_index,
                "valid": False,
                "error": error_msg
            })
        else:
            # Update the existing document info
            result["documents"][doc_index]["valid"] = False
            result["documents"][doc_index]["error"] = error_msg
            
        # Add detailed error info
        result["errors"].append({
            "type": "YAMLError",
            "message": error_msg,
            "path": str(file_path),
            "doc_index": doc_index
        })
        return result
        
    except Exception as e:
        result["success"] = False
        result["summary"]["valid"] = False
        result["summary"]["errors"] += 1
        result["errors"].append({
            "type": "Error",
            "message": f"Error reading file: {str(e)}",
            "path": str(file_path),
            "doc_index": 0  # Default to first document for general errors
        })
        return result

def validate_yaml_content(content: str) -> Dict[str, Any]:
    """
    Validate YAML content, supporting multiple YAML documents in a single string.
    
    Args:
        content (str): YAML content as string
        
    Returns:
        Dict[str, Any]: Validation results with the following structure:
        {
            'success': bool,          # Overall success status
            'summary': {
                'valid': bool,        # True if all YAML documents are valid
                'errors': int,        # Number of errors found
                'doc_count': int      # Number of YAML documents found
            },
            'documents': [            # List of validation results for each document
                {
                    'index': int,     # Document index (0-based)
                    'valid': bool,    # Validation status for this document
                    'error': str      # Error message if invalid (None if valid)
                }
            ],
            'errors': [              # Detailed error information
                {
                    'type': str,      # Error type (e.g., 'YAMLError')
                    'message': str,   # Error message
                    'doc_index': int  # Document index where error occurred
                }
            ]
        }
    """
    result = {
        "success": True,
        "summary": {"valid": True, "errors": 0, "doc_count": 0},
        "documents": [],
        "errors": []
    }
    
    try:
        # If content is empty or contains only whitespace, return success with doc_count=0
        if not content.strip():
            return result
            
        # Run yamllint to check for issues like duplicate keys
        yamllint_issues = run_yamllint(content)
        
        # Process all YAML documents in the content
        docs = list(yaml.safe_load_all(content))
        result["summary"]["doc_count"] = len(docs)
        
        # Group yamllint issues by document
        doc_issues = {}
        for issue in yamllint_issues:
            # Determine which document this issue belongs to based on line number
            # This is approximate as yamllint doesn't provide doc index directly
            doc_index = 0
            line_count = 0
            for i, doc_content in enumerate(content.split('---')):
                if i == 0 and not doc_content.strip():
                    continue  # Skip empty first document before first ---
                line_count += doc_content.count('\n') + 1  # +1 for the '---' line itself
                if issue["line"] <= line_count:
                    doc_index = i
                    break
            
            if doc_index not in doc_issues:
                doc_issues[doc_index] = []
            doc_issues[doc_index].append(issue)
        
        # Validate each document individually
        for i, doc in enumerate(docs):
            if doc is None:  # Empty document (just '---')
                result["documents"].append({
                    "index": i,
                    "valid": True,
                    "error": None
                })
                continue
            
            # Check if this document has issues
            if i in doc_issues and doc_issues[i]:
                # Document has issues
                issues = doc_issues[i]
                # Get the first error or warning if available
                error_issue = next((issue for issue in issues if issue["level"] == "error"), 
                                  next((issue for issue in issues), None))
                
                if error_issue:
                    error_msg = f"{error_issue['message']} ({error_issue['rule']}) at line {error_issue['line']}"
                    result["success"] = False
                    result["summary"]["valid"] = False
                    result["summary"]["errors"] += 1
                    
                    result["documents"].append({
                        "index": i,
                        "valid": False,
                        "error": error_msg
                    })
                    
                    # Add detailed error info for each issue in this document
                    for issue in issues:
                        # Create consistent error type format
                        if issue['rule'] == 'key-duplicates':
                            error_type = "DuplicateKeyError"
                        else:
                            error_type = f"YamlLint{issue['level'].capitalize()}"
                            
                        result["errors"].append({
                            "type": error_type,
                            "message": f"{issue['message']} ({issue['rule']}) at line {issue['line']}, column {issue['column']}",
                            "doc_index": i
                        })
                    continue
            
            # Document is valid
            result["documents"].append({
                "index": i,
                "valid": True,
                "error": None
            })
        
        return result
        
    except yaml.YAMLError as e:
        result["success"] = False
        result["summary"]["valid"] = False
        result["summary"]["errors"] += 1
        doc_index = getattr(e, 'problem_mark', None)
        if doc_index:
            # Get the document index from the error's problem_mark if available
            doc_index = doc_index.index
        else:
            doc_index = 0
            
        error_msg = f"Invalid YAML: {str(e)}"
        
        # Add document-specific error info
        if len(result["documents"]) <= doc_index:
            # If we haven't processed this document yet, add it
            result["documents"].append({
                "index": doc_index,
                "valid": False,
                "error": error_msg
            })
        else:
            # Update the existing document info
            result["documents"][doc_index]["valid"] = False
            result["documents"][doc_index]["error"] = error_msg
            
        # Add detailed error info
        result["errors"].append({
            "type": "YAMLError",
            "message": error_msg,
            "doc_index": doc_index
        })
        return result
        
    except Exception as e:
        result["success"] = False
        result["summary"]["valid"] = False
        result["summary"]["errors"] += 1
        result["errors"].append({
            "type": "Error",
            "message": f"Error parsing YAML: {str(e)}",
            "doc_index": 0  # Default to first document for general errors
        })
        return result
