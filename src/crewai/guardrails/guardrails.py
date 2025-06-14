"""
Guardrails module for ensuring the integrity of the devops flow.
"""

from src.crewai.devops_flow.blackboard.Blackboard import Blackboard
from src.crewai.devops_flow.blackboard.utils.Manifest import STATUS_IN_PROGRESS, STATUS_SOLVED, STATUS_PENDING

def check_manifest_status(
    blackboard: Blackboard, 
    status: str = STATUS_IN_PROGRESS,
    check_if_none: bool = True, 
    check_if_multiple: bool = True) -> None:
    """
    Ensure exactly one manifest is in the specified state after first_approach.
    
    Args:
        blackboard (Blackboard): The blackboard containing the manifests.
        status (str): The status to check for.
        check_if_none (bool): Whether to check if there is at least one manifest in the specified state.
        check_if_multiple (bool): Whether to check if there is more than one manifest in the specified state.
    
    Raises:
        ValueError: If no manifest or more than one manifest is marked as 'status'.
    """
    manifests = getattr(blackboard, "manifests", [])
    in_progress_count = sum(1 for m in manifests if getattr(m, "status", None) == status)
    if check_if_none and in_progress_count == 0:
        raise ValueError(
            f"After first_approach, at least one manifest must be in '{status}' state. "
            f"No manifest is currently marked as '{status}'. Check your flow logic or agent outputs."
        )
    if check_if_multiple and in_progress_count > 1:
        raise ValueError(
            f"After first_approach, only one manifest should be in '{status}' state. "
            f"Found {in_progress_count} manifests in '{status}'. Ensure your agent logic sets only one at a time."
        )