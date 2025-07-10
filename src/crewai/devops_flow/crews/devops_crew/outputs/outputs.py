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
    section: str = Field(..., description="Specific section of the code, where the issue was found and the solution will be applied. Use the yaml_edit tool format to specify one or more sections to be modified.")
    changes: str = Field(..., description="Modifications to be applied to the resource, to solve the issue. Use the yaml_edit tool format to specify the changes to be applied.")
    
class Solutions(BaseModel):
    solutions: List[Solution] = Field(..., description="List of solutions")
    