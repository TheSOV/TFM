import json
from pathlib import Path
from textwrap import dedent
import os
import json

from dotenv import load_dotenv
load_dotenv()

from src.crewai.tools.config_validator import ConfigValidatorTool

def run_validator_test():
    """Runs the validator on a specified YAML file and prints the result."""
    # Use the existing manifests.yaml file
    test_file = Path("d:\\Python\\MasterIA\\TFM\\TFM\\TFM\\temp\\project\\manifests.yaml")

    print(f"--- Validating file: {test_file} ---")

    # --- Instantiate and Run Tool ---
    # The file_path must be a string, so we convert the Path object.
    validator_tool = ConfigValidatorTool(file_path=str(test_file))
    result = validator_tool._run()
    
    # --- Print Validation Result ---
    print("\n--- Validation Result: ---")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    run_validator_test()

