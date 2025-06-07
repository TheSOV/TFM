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
            return (False, "No file was created")

        full_path = base_dir / Path(file_path)
        if not full_path.exists():
            return (False, f"File does not exist. Failed file: {file_path}")

        return (True, result)
    except Exception as e:
        return (False, f"Unexpected error during validation. Details: {str(e)}")

def _validate_create_k8s_config__llm_files_content(result: TaskOutput) -> Tuple[bool, Any]:
    guardrail = LLMGuardrail(
        description="Ensure that filepath is present, that the description is consistent, and the non-solved issues are properly explained.",
        llm=LLM(getenv("GUARDRAIL_MODEL"))
    )
    return guardrail(result)

def validate_create_k8s_config(result: TaskOutput) -> Tuple[bool, Any]:
    is_valid, feedback = _validate_create_k8s_config__files_exists(result)
    if not is_valid:
        return (is_valid, feedback)
    
    is_valid, feedback = _validate_create_k8s_config__llm_files_content(result)
    return (is_valid, feedback)

##
    

