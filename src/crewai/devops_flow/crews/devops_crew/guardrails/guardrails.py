from typing import Tuple, Any
from crewai import TaskOutput, LLMGuardrail
from crewai.llm import LLM
from pathlib import Path
from os import getenv

## Validate create k8s config
def _validate_create_k8s_config__files_exists(result: TaskOutput) -> Tuple[bool, Any]:
    try:
        file_path = result.json_dict.get("file_path", None)
        base_dir = Path(getenv("TEMP_FILES_DIR"))

        if not file_path:
            return (False, "Guardrail Message: No file_path was added to the output")

        full_path = base_dir / Path(file_path)
        if not full_path.exists():
            return (False, f"Guardrail Message: File does not exist. Failed file: {file_path}")

        namespace = result.json_dict.get("namespace", None)
        if not namespace:
            return (False, "Guardrail Message: No namespace was added to the output")

        # checkov_non_solved_issues = result.json_dict.get("checkov_non_solved_issues", None)
        # if not checkov_non_solved_issues:
        #     return (False, "No checkov non-solved issues were found")

        # images_data = result.json_dict.get("images_data", None)
        # if not images_data:
        #     return (False, "Guardrail Message: No images data were added to the output")

        return (True, result)
    except Exception as e:
        return (False, f"Guardrail Message: Unexpected error during validation. Details: {str(e)}")

def _validate_create_k8s_config__llm_files_content(result: TaskOutput) -> Tuple[bool, Any]:
    try:
        guardrail = LLMGuardrail(
            description="Ensure that file_path is present, namespace is present, and the non-solved issues exists (not empty list)",
            llm=LLM(getenv("GUARDRAIL_MODEL"))
        )
        is_valid, feedback = guardrail(result)
        # Ensure feedback is a string and not None
        feedback = feedback or "Validation passed"
        return (is_valid, feedback)
    except Exception as e:
        return (False, f"Guardrail validation error: {str(e)}")

def validate_create_k8s_config(result: TaskOutput) -> Tuple[bool, Any]:
    is_valid, feedback = _validate_create_k8s_config__files_exists(result)
    if not is_valid:
        return (is_valid, feedback)
    
    is_valid, feedback = _validate_create_k8s_config__llm_files_content(result)
    return (is_valid, feedback)
    
## Validate test k8s config
def validate_test_k8s_config(result: TaskOutput) -> Tuple[bool, Any]:
    try:
        json_dict = result.json_dict
        cluster_is_working = json_dict.get("cluster_working", None)
        if not isinstance(cluster_is_working, bool):
            return (False, "Guardrail Message: cluster_working is not a boolean")

        return (True, result)
    except Exception as e:
        return (False, f"Guardrail Message: Unexpected error during validation. Details: {str(e)}")

    

