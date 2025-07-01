from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Literal
from src.crewai.devops_flow.blackboard.utils.Manifest import Manifest
from src.crewai.devops_flow.blackboard.utils.Issue import Issue

class Issues(BaseModel):
    issues: List[Issue] = Field(..., description="List of issues")

class ImagesNames(BaseModel):
    images: List[str] = Field(..., description="List of images")

class Manifests(BaseModel):
    manifests: List[Manifest] = Field(..., description="List of manifests")

class Solution(BaseModel):
    issues: Issues = Field(..., description="Issues to which the solution applies")
    resource: str = Field(..., description="Resource where the issue was found and the solution will be applied")
    section: str = Field(..., description="Specific section of the code, where the issue was found and the solution will be applied")
    solution: str = Field(..., description="Modifications to be applied to the resource, to solve the issue")
    
class Solutions(BaseModel):
    solutions: List[Solution] = Field(..., description="List of solutions")
    