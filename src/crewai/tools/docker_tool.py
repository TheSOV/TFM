import json
import logging
from typing import Type, Dict, Any, List, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

logger = logging.getLogger(__name__)

from .utils.docker_utils import DockerUtils

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

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._docker_utils = DockerUtils()

    def _run(
        self,
        query: str,
        limit: int = 25,
        official_only: Optional[bool] = None,
        verified_only: Optional[bool] = None,
        sort_by_stars: bool = True,
    ) -> List[Dict[str, Any]]:
        try:
            results = self._docker_utils.search_images_cli(
                query=query,
                limit=limit,
                official_only=official_only,
                verified_only=verified_only,
                sort_by_stars=sort_by_stars,
            )
            return results
        except Exception as e:
            logger.error(f"Error during docker search for query '{query}': {e}", exc_info=True)
            # Return an empty list in case of an error to prevent crashing the agent
            return []


# ---------------------------------------------------------------------------
# NEW: Comprehensive Docker Image Analysis Tool
# ---------------------------------------------------------------------------

class DockerImageAnalysisInput(BaseModel):
    """Input schema for comprehensive Docker image analysis."""
    repository: str = Field(..., description="Docker repository name (e.g., 'library/redis')")
    tag: str = Field("latest", description="Image tag (default: 'latest')")


class DockerImageAnalysisTool(BaseTool):
    """
    Performs a comprehensive analysis of a Docker image.

    This tool retrieves detailed inspection information, user and group configurations,
    and potential writable locations within the specified Docker image.
    It consolidates all findings into a single JSON object.
    """

    name: str = "comprehensive_docker_image_analysis"
    description: str = (
        "Performs a comprehensive analysis of a Docker image, "
        "retrieving inspect details, user/group information, and "
        "potential writable locations. Returns all information as a single JSON object."
    )
    args_schema: Type[BaseModel] = DockerImageAnalysisInput
    _docker_utils: DockerUtils = PrivateAttr()

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._docker_utils = DockerUtils()

    def _run(self, repository: str, tag: str = "latest", **kwargs: Any) -> str:
        """
        Executes the comprehensive Docker image analysis.

        Args:
            repository: The Docker repository name.
            tag: The Docker image tag.

        Returns:
            A JSON string containing the analysis results.
        """
        results: Dict[str, Any] = {"image": f"{repository}:{tag}"}

        try:
            logger.info(f"Fetching inspect info for {repository}:{tag}")
            results["inspect_info"] = self._docker_utils.docker_inspect(repository=repository, tag=tag)
        except Exception as e:
            logger.error(f"Error during docker_inspect for {repository}:{tag}: {e}", exc_info=True)
            results["inspect_info"] = {"error": f"Failed to get inspect info: {str(e)}"}

        try:
            logger.info(f"Fetching user and group info for {repository}:{tag}")
            user_group_info = self._docker_utils.get_image_users_and_groups(repository=repository, tag=tag)
            results.update(user_group_info)
        except Exception as e:
            logger.error(f"Error during get_image_users_and_groups for {repository}:{tag}: {e}", exc_info=True)
            results["users_details"] = {"error": f"Failed to get user/group info: {str(e)}"}

        try:
            logger.info(f"Discovering writable locations for {repository}:{tag}")
            writable_locations_info = self._docker_utils.discover_image_writable_locations(repository=repository, tag=tag)
            results.update(writable_locations_info)
        except Exception as e:
            logger.error(f"Error during discover_image_writable_locations for {repository}:{tag}: {e}", exc_info=True)
            results["potential_writable_paths"] = {"error": f"Failed to discover writable locations: {str(e)}"}
        
        return results
