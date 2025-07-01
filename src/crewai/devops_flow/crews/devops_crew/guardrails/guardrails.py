from typing import Tuple, Any
from crewai import TaskOutput, LLMGuardrail
from crewai.llm import LLM
from pathlib import Path
from os import getenv

def validate_min_output_length_for_long_text(result: TaskOutput) -> Tuple[bool, Any]:
    if len(result.raw) < 1000:
        return (False, f"Guardrail Message: Output is too short. You possibly did provide the report as answer, and instead used a failed tool call or a reference to the final report. Your final answer was: '{result.raw}', and it should be a report that complies with the task")
    return (True, result)

# ## Validate create k8s config
# def _validate_create_k8s_config__files_exists(result: TaskOutput) -> Tuple[bool, Any]:
#     try:
#         file_path = result.json_dict.get("file_path", None)
#         base_dir = Path(getenv("TEMP_FILES_DIR"))

#         if not file_path:
#             return (False, "Guardrail Message: No file_path was added to the output")

#         full_path = base_dir / Path(file_path)
#         if not full_path.exists():
#             return (False, f"Guardrail Message: File does not exist. Failed file: {file_path}")

#         namespace = result.json_dict.get("namespace", None)
#         if not namespace:
#             return (False, "Guardrail Message: No namespace was added to the output")

#         # checkov_non_solved_issues = result.json_dict.get("checkov_non_solved_issues", None)
#         # if not checkov_non_solved_issues:
#         #     return (False, "No checkov non-solved issues were found")

#         # images_data = result.json_dict.get("images_data", None)
#         # if not images_data:
#         #     return (False, "Guardrail Message: No images data were added to the output")

#         return (True, result)
#     except Exception as e:
#         return (False, f"Guardrail Message: Unexpected error during validation. Details: {str(e)}")

# def _validate_create_k8s_config__llm_files_content(result: TaskOutput) -> Tuple[bool, str]:
#     """
#     Validate the Kubernetes configuration files content using LLM guardrail.
    
#     Args:
#         result (TaskOutput): The task output containing the configuration to validate.
        
#     Returns:
#         Tuple[bool, str]: A tuple containing:
#             - bool: True if validation passed, False otherwise
#             - str: Feedback message about the validation result
#     """
#     try:
#         guardrail = LLMGuardrail(
#             description=(
#                 "Ensure that file_path is present, namespace is present, "
#                 "and the non-solved issues exist (not empty list). "
#                 "Return feedback as a string, never as None."
#             ),
#             llm=LLM(getenv("GUARDRAIL_MODEL"))
#         )
        
#         # Get validation result and ensure feedback is a string
#         is_valid, feedback = guardrail(result)
        
#         # Ensure feedback is a non-empty string
#         if not feedback or not isinstance(feedback, str):
#             feedback = "Validation completed with no specific feedback"
            
#         return (is_valid, feedback)
        
#     except Exception as e:
#         error_msg = f"Guardrail validation error: {str(e)}"
#         return (False, error_msg)

# def validate_create_k8s_config(result: TaskOutput) -> Tuple[bool, Any]:
#     is_valid, feedback = _validate_create_k8s_config__files_exists(result)
#     # if not is_valid:
#     #     return (is_valid, feedback)
    
#     # is_valid, feedback = _validate_create_k8s_config__llm_files_content(result)
#     return (is_valid, feedback)
    
# ## Validate test k8s config
# def validate_test_k8s_config(result: TaskOutput) -> Tuple[bool, Any]:
#     try:
#         json_dict = result.json_dict
#         cluster_is_working = json_dict.get("cluster_working", None)
#         if not isinstance(cluster_is_working, bool):
#             return (False, "Guardrail Message: cluster_working is not a boolean")

#         return (True, result)
#     except Exception as e:
#         return (False, f"Guardrail Message: Unexpected error during validation. Details: {str(e)}")

    
