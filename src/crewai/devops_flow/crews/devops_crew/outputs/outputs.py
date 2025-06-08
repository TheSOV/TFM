from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Literal

# Severity of the issue (must be one of: 'low', 'medium', 'high', 'very_high')
_SeverityType = Literal["low", "medium", "high", "very_high"]

# Issue found by the agent
class _Issues(BaseModel):
    issue: str = Field(..., description="Issue found by the agent")
    severity: _SeverityType = Field(..., description="Severity of the issue (must be one of: 'low', 'medium', 'high', 'very_high')")
    description: str = Field(..., description="Description of the issue")

## Output of the image data retrieval task
class _ImageDataRetrievalOutput(BaseModel):
    latest_stable_tag: str = Field(..., description="Latest stable tag of the image")    
    repository: str = Field(..., description="Repository of the image")
    image_name: str = Field(..., description="Image name of the image")
    version: str = Field(..., description="Version of the image")
    manifest_digest: str = Field(..., description="Manifest digest, to get image details")
    pullable_digest: str = Field(..., description="Pullable digest of the image")
    ports: List[int] = Field(..., description="Ports of the image")
    volumes: List[str] = Field(..., description="Volumes of the image")
    environment_variables: List[str] = Field(..., description="Environment variables of the image")
    description: str = Field(..., description="A general description of the image, including all representative information")

class ImagesDataRetrievalOutput(BaseModel):
    image_data: List[_ImageDataRetrievalOutput] = Field(..., description="Images data retrieved by the agent")

## Output of the Create K8s Config Task
class CreateK8sConfigOutput(BaseModel):
    file_path: str = Field(..., description="Path of the file created by the agent")
    namespace: str = Field(..., description="Namespace of the k8s config created by the agent")
    checkov_non_solved_issues: List[_Issues] = Field(..., description="List of non-solved issues found by the agent during the checkov analysis, if it was executed.")

## Output of the test k8s config task
class TestK8sConfigOutput(BaseModel):
    cluster_issues: List[_Issues] = Field(..., description="List of issues found by the agent")
    cluster_working: bool = Field(..., description="Whether the cluster is working as expected")

