from pydantic import BaseModel, Field
from typing import List


class CreateK8sConfigOutput(BaseModel):
    file_path: str = Field(..., description="Path of the file created by the agent")
    summary: str = Field(..., description="Summary of the task completed by the agent")
    non_solved_issues: List[str] = Field(..., description="List of non-solved issues found by the agent")
    