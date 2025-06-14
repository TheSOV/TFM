import json
import logging
from typing import Type, Dict, Any, List, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

logger = logging.getLogger(__name__)

from .utils.docker_registry_client import DockerRegistryClient


class GetDockerManifestInput(BaseModel):
    """Input schema for getting Docker image manifest."""
    repository: str = Field(..., description="Docker repository name (e.g., 'library/redis')")
    tag: str = Field("latest", description="Image tag (default: 'latest')")


class GetImageDetailsInput(BaseModel):
    """Input schema for getting Docker image details."""
    repository: str = Field(..., description="Docker repository name (e.g., 'library/redis')")
    digest: str = Field(..., description="Image digest from the manifest")

class DockerPullableDigestInput(BaseModel):
    """Input schema for getting pullable digest of a Docker image."""
    repository: str = Field(..., description="Docker repository name (e.g., 'library/redis')")
    tag: str = Field("latest", description="Image tag (default: 'latest')")

class DockerManifestTool(BaseTool):
    """Tool to get the manifest of a Docker image from a registry."""
    name: str = "get_docker_manifest"
    description: str = "Get the manifest of a Docker image from a registry. The digests present in the results of this tool are NOT pullable digests. They are the digests used to get the details of the image. If you try to use them to pull the image, it will fail. Use the get_docker_pullable_digest tool to get pullable digests."
    args_schema: Type[BaseModel] = GetDockerManifestInput
    
    _registry_client: DockerRegistryClient = PrivateAttr()
    
    def __init__(self, registry_client: DockerRegistryClient, **kwargs):
        super().__init__(**kwargs)
        self._registry_client = registry_client
    
    def _run(self, repository: str, tag: str = "latest") -> str:
        """
        Get the manifest for a Docker image.
        
        Args:
            repository: Docker repository name (e.g., 'library/redis')
            tag: Image tag (default: 'latest')
            
        Returns:
            str: JSON string containing the manifest information
        """
        manifest = self._registry_client.get_manifest(repository, tag)
        return manifest


class DockerImageDetailsTool(BaseTool):
    """Tool to get detailed configuration of a Docker image using its manifest digest."""
    name: str = "get_docker_image_details"
    description: str = "Get detailed configuration of a Docker image using its manifest digest."
    args_schema: Type[BaseModel] = GetImageDetailsInput
    
    _registry_client: DockerRegistryClient = PrivateAttr()
    
    def __init__(self, registry_client: DockerRegistryClient, **kwargs):
        super().__init__(**kwargs)
        self._registry_client = registry_client
    
    def _run(self, repository: str, digest: str) -> str:
        """
        Get detailed configuration for a Docker image.
        
        Args:
            repository: Docker repository name (e.g., 'library/redis')
            digest: Image digest from the manifest
            
        Returns:
            str: JSON string containing the image configuration
        """
        details = self._registry_client.get_image_details(repository, digest)
        return details

class DockerPullableDigestTool(BaseTool):
    """Tool to get the pullable digest of a Docker image using 'docker inspect'."""
    name: str = "get_docker_pullable_digest"
    description: str = "Get the pullable digest of a Docker image using 'docker inspect'. The digest returned by this tool is the one that can be used to pull the image."
    args_schema: Type[BaseModel] = DockerPullableDigestInput
    
    _registry_client: DockerRegistryClient = PrivateAttr()
    
    def __init__(self, registry_client: DockerRegistryClient, **kwargs):
        super().__init__(**kwargs)
        self._registry_client = registry_client
    
    def _run(self, repository: str, tag: str = "latest") -> str:
        """
        Get the pullable digest for a Docker image.
        
        Args:
            repository: Docker repository name (e.g., 'nginx' or 'library/redis')
            tag: Image tag (default: 'latest')
            
        Returns:
            str: Pullable digest in format 'repository@sha256:digest' or error message
        """
        try:
            return self._registry_client.get_pullable_digest(repository, tag)
        except Exception as e:
            error_msg = f"Error getting pullable digest for {repository}:{tag}: {str(e)}"
            logger.error(error_msg)
            return error_msg


# ---------------------------------------------------------------------------
# NEW: Search images in Docker Hub via local Docker CLI
# ---------------------------------------------------------------------------

class SearchDockerImagesInput(BaseModel):
    """Input schema for searching Docker Hub images using the local Docker CLI."""

    query: str = Field(..., description="Search term, e.g. 'redis'.")
    limit: int = Field(25, description="Maximum number of results (1-100).")
    official_only: Optional[bool] = Field(
        None,
        description="If True, return only official images; False, only non-official; None, no filter.",
    )
    verified_only: Optional[bool] = Field(
        None,
        description="Filter by verified publisher flag similarly to *official_only*.",
    )
    sort_by_stars: bool = Field(
        True,
        description="Sort results descending by star count (default True).",
    )


class DockerSearchImagesTool(BaseTool):
    """Search Docker Hub images through the local Docker CLI (`docker search`).

    Unlike the manifest/detail tools that hit the Registry HTTP API, this tool
    returns a list of dictionaries with keys:

    ``full_name``: repository name (e.g. ``redis`` or ``bitnami/redis``)
    ``description``: short description
    ``official``: bool flag for official images
    ``verified``: bool flag for verified publishers (if available)
    ``automated``: bool flag for automated builds
    ``stars``: star count (int)
    """

    name: str = "search_docker_images"
    description: str = (
        "Search Docker Hub images using the local Docker CLI. Supports limit, "
        "official/verified filters and star-count sorting. Returns a JSON list "
        "of dictionaries with full_name, description, official, verified, "
        "automated and stars fields. Official images are located at library/name_of_image, and will have "
        "official=True and verified=False. Verified images are has custom repo name and will have "
        "verified=True and official=False."
    )
    args_schema: Type[BaseModel] = SearchDockerImagesInput

    _registry_client: DockerRegistryClient = PrivateAttr()

    def __init__(self, registry_client: DockerRegistryClient, **kwargs):
        super().__init__(**kwargs)
        self._registry_client = registry_client

    def _run(
        self,
        query: str,
        limit: int = 25,
        official_only: Optional[bool] = None,
        verified_only: Optional[bool] = None,
        sort_by_stars: bool = True,
    ) -> List[Dict[str, Any]]:
        results = self._registry_client.search_images_cli(
            query=query,
            limit=limit,
            official_only=official_only,
            verified_only=verified_only,
            sort_by_stars=sort_by_stars,
        )
        return results
