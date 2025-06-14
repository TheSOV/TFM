from pydantic import BaseModel, Field
from typing import Literal

SEVERITY_LOW: str = "LOW"
SEVERITY_MEDIUM: str = "MEDIUM"
SEVERITY_HIGH: str = "HIGH"
SEVERITY_TYPE = Literal[SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH]

class Issue(BaseModel):
    issue: str = Field(..., description="Brief and ilustrative title of the issue")
    severity: SEVERITY_TYPE = Field(..., description=f"Severity of the issue (must be one of: {SEVERITY_TYPE}).")
    problem_description: str = Field(..., description="Complete description of the issue, with all the details and context")
    possible_manifest_file_path: str = Field(..., description="Path to the manifest file that might be the cause of the issue")
    observations: str = Field(..., description="Any additional observations or comments")