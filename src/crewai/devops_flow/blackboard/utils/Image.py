from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class InspectInfo(BaseModel):
    repo_digest: Optional[str] = Field(None, description="The repository digest of the image.")
    user: Optional[str] = Field(None, description="User and group that runs the container process.")
    exposed_ports: Optional[List[str]] = Field(None, description="List of ports exposed by the image.")
    volumes: Optional[List[str]] = Field(None, description="List of volumes defined in the image.")
    entrypoint: Optional[List[str]] = Field(None, description="The entrypoint for the container.")
    cmd: Optional[List[str]] = Field(None, description="The default command to be executed.")
    env_vars: Optional[List[str]] = Field(None, description="List of environment variables.")
    working_dir: Optional[str] = Field(None, description="The working directory inside the container.")
    stop_signal: Optional[str] = Field(None, description="The signal to stop the container.")
    labels: Optional[Dict[str, str]] = Field(None, description="Labels associated with the image.")
    architecture: Optional[str] = Field(None, description="The architecture of the image.")
    os: Optional[str] = Field(None, description="The operating system of the image.")
    created: Optional[str] = Field(None, description="The creation timestamp of the image.")
    docker_version: Optional[str] = Field(None, description="The Docker version used to build the image.")
    size: Optional[int] = Field(None, description="The size of the image in bytes.")
    media_type: Optional[str] = Field(None, description="The media type of the image manifest.")
    error: Optional[str] = Field(None, description="An error message if inspection failed.")

class SupplementaryGroup(BaseModel):
    gid: str = Field(..., description="Group ID.")
    group_name: str = Field(..., description="Group name.")

class UserDetails(BaseModel):
    username: str = Field(..., description="The name of the user.")
    uid: str = Field(..., description="The user ID.")
    primary_gid: str = Field(..., description="The primary group ID of the user.")
    primary_group_name: Optional[str] = Field(None, description="The name of the primary group.")
    supplementary_groups: List[SupplementaryGroup] = Field(default_factory=list, description="List of supplementary groups the user belongs to.")

class Image(BaseModel):
    image_name: str = Field(..., description="The full image reference, e.g., 'library/redis:latest'.")
    repository: str = Field(..., description="Repository of the image, e.g., 'library/redis'.")
    tag: str = Field(..., description="Tag of the image, e.g., 'latest'.")
    inspect_info: Optional[InspectInfo] = Field(None, description="Detailed information from 'docker inspect'.")
    users_details: Optional[List[UserDetails]] = Field(None, description="List of users and their group memberships within the image.")
    potential_writable_paths: Optional[List[str]] = Field(None, description="List of potential world-writable paths in the image.")
    error: Optional[str] = Field(None, description="An error message if the overall analysis failed.")
    k8s_tips: Optional[List[str]] = Field(None, description="List of tips for using the image with Kubernetes.")