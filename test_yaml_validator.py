#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YAML Validator Test

Test the YAML validator with a file containing duplicate keys.
"""

from pathlib import Path
from src.crewai.tools.utils.yaml_validator import validate_yaml_file
import pprint

def test_duplicate_keys():
    """
    Test detection of duplicate keys in a Kubernetes YAML file.
    
    Tests the yamllint integration by validating a YAML file with duplicate keys
    (specifically a duplicate securityContext in a Kubernetes manifest).
    
    Returns:
        None
    """
    # Path to test file with duplicate keys
    test_file = Path("test_duplicate_keys.yaml")
    
    # Validate the file
    result = validate_yaml_file(test_file)
    
    # Print the validation result
    print("\nYAML Validation Result:")
    pprint.pprint(result)
    
    # Check if duplicates were found
    if not result["summary"]["valid"]:
        print("\nFound YAML issues:")
        for error in result["errors"]:
            print(f"\n- {error['message']}")
    else:
        print("\nNo issues found.")

if __name__ == "__main__":
    test_duplicate_keys()
