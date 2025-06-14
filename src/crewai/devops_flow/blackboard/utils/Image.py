from pydantic import BaseModel, Field
from typing import List

class Image(BaseModel):
    tag: str = Field(..., description="Tag of the image version ready for production.")    
    repository: str = Field(..., description="Repository of the image")
    image_name: str = Field(..., description="Image name of the image")
    version: str = Field(..., description="Version number of the image")
    manifest_digest: str = Field(..., description="Manifest digest, to get image details")
    pullable_digest: str = Field(..., description="Pullable digest of the image")
    ports: List[int] = Field(..., description="Ports of the image exposed by the image")
    volumes: List[str] = Field(..., description="Volumes of the image")
    environment_variables: List[str] = Field(..., description="Environment variables of the image")
    description: str = Field(..., description="A general description of the image, including all representative information")