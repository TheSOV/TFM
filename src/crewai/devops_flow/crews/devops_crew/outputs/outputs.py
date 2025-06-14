from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Literal
from src.crewai.devops_flow.blackboard.utils.Manifest import Manifest
from src.crewai.devops_flow.blackboard.utils.Image import Image
from src.crewai.devops_flow.blackboard.utils.Issue import Issue

class Issues(BaseModel):
    issues: List[Issue] = Field(..., description="List of issues")

class ImagesNames(BaseModel):
    images: List[str] = Field(..., description="List of images")

class Images(BaseModel):
    images: List[Image] = Field(..., description="List of images")

class Manifests(BaseModel):
    manifests: List[Manifest] = Field(..., description="List of manifests")
    
