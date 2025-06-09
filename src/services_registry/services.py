from typing import Callable, Any, Dict, Tuple, Optional
import os

from src.embeddings.late_chunking import LateChunkingHelper
from src.database.weviate import WeaviateHelper
from src.ingest.ingest_helper import IngestHelper

from src.crewai.tools.file_edit_tool import FileCreateTool, FileEditTool, FileReadTool  
from src.crewai.tools.config_validator import ConfigValidatorTool
from src.crewai.tools.kubectl_tool import KubectlTool
from src.crewai.tools.rag_tool import RagTool
from src.crewai.tools.docker_registry_tool import DockerManifestTool, DockerImageDetailsTool, DockerPullableDigestTool
from src.crewai.tools.utils.docker_registry_client import DockerRegistryClient, DockerRegistryAuth
from src.crewai.tools.popeye_scan_tool import PopeyeScanTool
from src.crewai.tools.file_version_history_tool import FileVersionHistoryTool, FileVersionDiffTool, FileVersionRestoreTool
from src.version_control.versioning_utils import FileVersioning

from crewai_tools import DirectoryReadTool
from crewai_tools import SeleniumScrapingTool


_registry: Dict[str, Tuple[Callable[[], Any], bool]] = {}
_cache:    Dict[str, Any] = {}

def init_services():
    register("late_chunking_helper", 
    lambda: LateChunkingHelper(
        model_name=os.getenv("LATE_CHUNKING_MODEL_NAME"), 
        headers_to_split_on=os.getenv("LATE_CHUNKING_HEADERS_TO_SPLIT_ON"), 
        max_chunk_chars=int(os.getenv("LATE_CHUNKING_MAX_CHUNK_CHARS")), 
        device=os.getenv("LATE_CHUNKING_DEVICE")
    ))
    
    register("weaviate_helper", 
    lambda: WeaviateHelper(
        weaviate_api_key=os.getenv("WEAVIATE_API_KEY"), 
        weaviate_host=os.getenv("WEAVIATE_HOST"), 
        weaviate_port=os.getenv("WEAVIATE_PORT"), 
        weaviate_grpc_port=os.getenv("WEAVIATE_GRPC_PORT")
    ))

    register("ingest_helper", 
    lambda: IngestHelper(
        knowledge_summary_model=os.getenv("INGEST_KNOWLEDGE_SUMMARY_MODEL"), 
        knowledge_config_path=os.getenv("INGEST_KNOWLEDGE_CONFIG_PATH"), 
        override_collection=os.getenv("INGEST_KNOWLEDGE_OVERRIDE_COLLECTION"), 
        weaviate_helper=get("weaviate_helper"), 
        late_chunking_helper=get("late_chunking_helper")
    ))

    register("rag", 
    lambda: RagTool(
        weaviate_helper=get("weaviate_helper"),
        late_chunking_helper=get("late_chunking_helper")
    ), singleton=False)

    # Register kubectl tool with configuration from environment
    def get_namespace_set(env_var: str) -> Optional[set]:
        value = os.getenv(env_var, "").strip()
        if not value:
            return None
        return set(filter(None, value.split(",")))
        
    register("kubectl",
    lambda: KubectlTool(
        kubectl_path=os.getenv("KUBECTL_PATH", "/usr/bin/kubectl"),
        allowed_verbs=set(filter(None, os.getenv("KUBECTL_ALLOWED_VERBS", "").split(","))),
        safe_namespaces=get_namespace_set("KUBECTL_SAFE_NAMESPACES"),
        denied_namespaces=get_namespace_set("KUBECTL_DENIED_NAMESPACES") or set(),
        deny_flags=set(filter(None, os.getenv("KUBECTL_DENY_FLAGS", "").split(","))),
        base_dir=os.getenv("TEMP_FILES_DIR", "/temp")  # Use same base dir as other file operations
    ), singleton=False)

    # Register FileVersioning as a singleton
    register("file_versioning", 
    lambda: FileVersioning(
        repo_path=os.getenv("TEMP_FILES_DIR")
    ), singleton=True)
    
    register("file_create", 
    lambda: FileCreateTool(
        base_dir=os.getenv("TEMP_FILES_DIR"),
        versioning=get("file_versioning")
    ), singleton=False)

    register("file_edit", 
    lambda: FileEditTool(
        base_dir=os.getenv("TEMP_FILES_DIR"),
        versioning=get("file_versioning")
    ), singleton=False)

    register("file_read", 
    lambda: FileReadTool(
        base_dir=os.getenv("TEMP_FILES_DIR")
    ), singleton=False)

    register("file_version_history", 
    lambda: FileVersionHistoryTool(
        base_dir=os.getenv("TEMP_FILES_DIR"),
        versioning=get("file_versioning")
    ), singleton=False)

    register("file_version_diff", 
    lambda: FileVersionDiffTool(
        base_dir=os.getenv("TEMP_FILES_DIR"),
        versioning=get("file_versioning")
    ), singleton=False)

    register("file_version_restore", 
    lambda: FileVersionRestoreTool(
        base_dir=os.getenv("TEMP_FILES_DIR"),
        versioning=get("file_versioning")
    ), singleton=False)

    register("config_validator", 
    lambda: ConfigValidatorTool(
        base_dir=os.getenv("TEMP_FILES_DIR")
    ), singleton=False)

    # Register Docker Registry tools
    register("docker_registry_auth",
    lambda: DockerRegistryAuth(
        username=os.getenv("DOCKER_REGISTRY_USERNAME"),
        password=os.getenv("DOCKER_REGISTRY_PASSWORD"),
        registry=os.getenv("DOCKER_REGISTRY_URL", "registry-1.docker.io")
    ))

    register("docker_registry_client",
    lambda: DockerRegistryClient(
        auth=get("docker_registry_auth")
    ))

    register("docker_manifest_tool",
    lambda: DockerManifestTool(
        registry_client=get("docker_registry_client")
    ), singleton=False)

    register("docker_image_details_tool",
    lambda: DockerImageDetailsTool(
        registry_client=get("docker_registry_client")
    ), singleton=False)
    
    register("docker_pullable_digest_tool",
    lambda: DockerPullableDigestTool(
        registry_client=get("docker_registry_client")
    ), singleton=False)
    
    # Register Popeye scan tool
    register("popeye_scan",
    lambda: PopeyeScanTool(
        popeye_path=os.getenv("POPEYE_PATH", "popeye")
    ), singleton=False)


def register(name: str,
             factory: Callable[[], Any],
             *,
             singleton: bool = True) -> None:
    """Añade un servicio al registro (lazy)."""
    _registry[name] = (factory, singleton)

def get(name: str) -> Any:
    """Devuelve la instancia; la crea la primera vez si es singleton."""
    factory, singleton = _registry[name]
    if singleton:
        if name not in _cache:
            _cache[name] = factory()          # creación diferida
        return _cache[name]
    return factory()                          # nuevo objeto cada llamada

def reset_cache():                            # útil en tests
    _cache.clear()



