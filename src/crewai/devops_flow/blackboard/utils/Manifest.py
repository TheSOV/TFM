from pydantic import BaseModel, Field
from typing import List, Optional
from src.crewai.devops_flow.blackboard.utils.Image import Image

class Manifest(BaseModel):
    title: str = Field(..., description="Identificative name of the manifest")
    last_working_index_version: Optional[str] = Field(default=None, description="Last working version of the file")
    namespace: str = Field(..., description="Namespace of the manifest")
    description: str = Field(..., description="A general description of the manifest, including all representative information")
    

