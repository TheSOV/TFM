"""
Docker Registry Client for interacting with Docker Registry API.
This is a utility class that provides common functionality for Docker registry operations.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from dxf import DXF
import json
import subprocess
from pprint import pprint

class DockerRegistryAuth(BaseModel):
    """Authentication details for Docker Registry."""
    username: str = Field(..., description="Username for Docker Registry authentication")
    password: str = Field(..., description="Password or token for Docker Registry authentication")
    registry: str = Field(
        "registry-1.docker.io",
        description="Docker registry URL. Defaults to Docker Hub."
    )


class DockerRegistryClient:
    """
    Client for interacting with Docker Registry.
    This is a utility class that provides common functionality for Docker registry operations.
    """
    def __init__(self, auth: DockerRegistryAuth):
        """
        Initialize the Docker Registry client with authentication details.
        
        Args:
            auth: DockerRegistryAuth containing username, password, and registry URL
        """
        self._auth = auth
        self._dxf = None
        self._current_repo = None

    def _get_dxf(self, repository: str):
        """Get or create a DXF instance for the given repository."""
        if self._dxf is None or self._current_repo != repository:
            self._dxf = DXF(self._auth.registry, repository)
            self._current_repo = repository
            self._dxf.authenticate(
                username=self._auth.username,
                password=self._auth.password,
                actions=["pull"]  # read-only access
            )
        return self._dxf

    def get_manifest(self, repository: str, tag: str) -> Dict[str, Any]:
        """
        Get the manifest for a Docker image.
        
        Args:
            repository: Docker repository name (e.g., 'library/redis')
            tag: Image tag (default: 'latest')
            
        Returns:
            Dict containing the manifest information
        """
        dxf = self._get_dxf(repository)
        manifest = dxf.get_manifest(tag)
        return manifest

    def get_image_details(self, repository: str, digest: str) -> Dict[str, Any]:
        """
        Get detailed configuration for a Docker image using its digest.
        
        Args:
            repository: Docker repository name (e.g., 'library/redis')
            digest: Image digest from the manifest
            
        Returns:
            Dict containing the image configuration
        """
        dxf = self._get_dxf(repository)
        config_blob = dxf.pull_blob(digest)
        
        # Handle both bytes and iterator responses
        if isinstance(config_blob, (bytes, bytearray)):
            config_data = config_blob
        else:
            config_data = b"".join(config_blob)
            
        return json.loads(config_data)

    def get_pullable_digest(self, repository: str, tag: str = "latest") -> str:
        """
        Get the pullable digest for a Docker image by pulling it if necessary and then inspecting it.

        Args:
            repository: Docker repository name (e.g., 'library/redis')
            tag: Image tag (default: 'latest')

        Returns:
            str: Pullable image digest in format 'repository@sha256:digest'

        Raises:
            RuntimeError: If the docker commands fail or return unexpected output
        """
        image_ref = f"{repository}:{tag}" if tag else repository
        
        def _run_docker_command(cmd: list) -> subprocess.CompletedProcess:
            """Helper to run docker commands with consistent error handling."""
            try:
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"Command '{' '.join(cmd)}' failed with error: {e.stderr}"
                )
        
        # First, try to pull the image
        try:
            pull_cmd = ["docker", "pull", image_ref]
            _run_docker_command(pull_cmd)
        except Exception as e:
            raise RuntimeError(f"Failed to pull image {image_ref}: {str(e)}")
        
        # Then inspect the image to get the digest
        try:
            inspect_cmd = ["docker", "inspect", image_ref, "--format={{index .RepoDigests 0}}"]
            result = _run_docker_command(inspect_cmd)
            output = result.stdout.strip()
            
            if not output:
                raise RuntimeError(f"No digest found for {image_ref}")
            
            # The output should be in format 'repository@sha256:digest'
            if '@sha256:' not in output:
                raise RuntimeError(f"Unexpected digest format: {output}")
            
            return output
            
        except Exception as e:
            raise RuntimeError(f"Failed to inspect image {image_ref}: {str(e)}")

    def search_images_cli(
        self,
        query: str,
        limit: int = 25,
        official_only: Optional[bool] = None,
        verified_only: Optional[bool] = None,
        sort_by_stars: bool = True,
    ) -> List[Dict]:
        """Search Docker Hub images via ``docker search`` CLI.

        Parameters
        ----------
        query : str
            Search term.
        limit : int, default 25
            Maximum results to return (CLI supports up to 100).
        official_only : bool | None, default None
            If True, return only official images; False, only non-official;
            None, no filter.
        verified_only : bool | None, default None
            Filter by *verified publisher* flag similarly.
        sort_by_stars : bool, default True
            Sort results descending by stars.

        Returns
        -------
        List[Dict]
            Each dict contains ``full_name``, ``description``, ``official``,
            ``verified``, ``stars`` (int).
        """

        format_str = "{{json .}}"  # each result line as JSON

        cmd = [
            "docker",
            "search",
            "--format",
            format_str,
            "--limit",
            str(limit),
            query,
        ]

        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"docker search failed: {exc.stderr or exc.stdout}"
            ) from exc

        results: List[Dict] = []

        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Values from docker search are strings ("true" / "false")
            def _as_bool(val: str | bool | None) -> bool:
                if isinstance(val, bool):
                    return val
                if isinstance(val, str):
                    return val.lower() == "true" or val.lower() == "[ok]"
                return False

            info = {
                "full_name": item.get("Name"),
                "description": item.get("Description", ""),
                "official": _as_bool(item.get("IsOfficial")),
                "verified": _as_bool(item.get("IsTrusted")),
                "automated": _as_bool(item.get("IsAutomated")),
                "stars": int(item.get("StarCount", 0)),
            }

            if (
                (official_only is None or info["official"] == official_only)
                and (verified_only is None or info["verified"] == verified_only)
            ):
                results.append(info)

        if sort_by_stars:
            results.sort(key=lambda x: x["stars"], reverse=True)

        return results
