from typing import Callable, Any, Dict, Tuple, Optional
import os
import threading

from src.embeddings.late_chunking import LateChunkingHelper
from src.database.weviate import WeaviateHelper
from src.ingest.ingest_helper import IngestHelper

from src.crewai.tools.file_edit_tool import FileCreateTool, FileEditTool, FileReadTool  
from src.crewai.tools.config_validator import ConfigValidatorTool
from src.crewai.tools.kubectl_tool import KubectlTool
from src.crewai.tools.rag_tool import RagTool
from src.crewai.tools.docker_tool import DockerSearchImagesTool, DockerImageAnalysisTool
from src.crewai.tools.popeye_scan_tool import PopeyeScanTool
from src.crewai.tools.file_version_history_tool import FileVersionHistoryTool, FileVersionDiffTool, FileVersionRestoreTool
from src.crewai.tools.blackboard_tool import BlackboardTool
from src.crewai.tools.stack_tool import StackOverflowSearchTool
from src.crewai.tools.web_browser_tool import WebBrowserTool
from src.version_control.versioning_utils import FileVersioning
from src.crewai.devops_flow.blackboard.Blackboard import Blackboard

from crewai_tools import BraveSearchTool


_registry: Dict[str, Tuple[Callable[[], Any], bool]] = {}
_cache:    Dict[str, Any] = {}

def init_services_with_path(path: str):
    # Use a sensible default 'temp' instead of `path` to avoid creating incorrect paths like 'project/project'
    temp_files_dir = os.getenv("TEMP_FILES_DIR", "temp")
    full_path = os.path.join(temp_files_dir, path)

    # Register kubectl tool with configuration from environment
    def get_namespace_set(env_var: str) -> Optional[set]:
        value = os.getenv(env_var, "").strip()
        if not value:
            return None
        return set(filter(None, value.split(",")))

    register(f"kubectl_{path}",
    lambda: KubectlTool(
        kubectl_path=os.getenv("KUBECTL_PATH", "/usr/bin/kubectl"),
        allowed_verbs=set(filter(None, os.getenv("KUBECTL_ALLOWED_VERBS", "").split(","))),
        safe_namespaces=get_namespace_set("KUBECTL_SAFE_NAMESPACES"),
        denied_namespaces=get_namespace_set("KUBECTL_DENIED_NAMESPACES") or set(),
        deny_flags=set(filter(None, os.getenv("KUBECTL_DENY_FLAGS", "").split(","))),
        base_dir=full_path
    ), singleton=False)

    # Register FileVersioning as a singleton
    register(f"file_versioning_{path}", 
    lambda: FileVersioning(
        repo_path=full_path
    ), singleton=True)
    
    register(f"file_create_{path}", 
    lambda: FileCreateTool(
        base_dir=full_path,
        versioning=get(f"file_versioning_{path}"),
        enable_versioning=True
    ), singleton=False)

    register(f"file_edit_{path}", 
    lambda: FileEditTool(
        base_dir=full_path,
        versioning=get(f"file_versioning_{path}"),
        enable_versioning=True
    ), singleton=False)

    register(f"file_read_{path}", 
    lambda: FileReadTool(
        base_dir=full_path
    ), singleton=False)

    register(f"file_version_history_{path}", 
    lambda: FileVersionHistoryTool(
        base_dir=full_path,
        versioning=get(f"file_versioning_{path}")
    ), singleton=False)

    register(f"file_version_diff_{path}", 
    lambda: FileVersionDiffTool(
        base_dir=full_path,
        versioning=get(f"file_versioning_{path}")
    ), singleton=False)

    register(f"file_version_restore_{path}", 
    lambda: FileVersionRestoreTool(
        base_dir=full_path,
        versioning=get(f"file_versioning_{path}")
    ), singleton=False)

    register(f"config_validator_{path}", 
    lambda: ConfigValidatorTool(
        base_dir=full_path
    ), singleton=False)
    

def init_services():
    # Register Blackboard as a singleton
    register("blackboard", lambda: Blackboard(), singleton=True)
    

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

    
    # Register other services here as needed
    register("kill_signal_event", lambda: threading.Event(), singleton=True) # Ensure threading is imported


    register("docker_image_analysis_tool", 
    lambda: DockerImageAnalysisTool(), singleton=False)

    
    register("docker_search_images_tool",
    lambda: DockerSearchImagesTool(), singleton=False)
    
    # Register Popeye scan tool
    register("popeye_scan",
    lambda: PopeyeScanTool(
        popeye_path=os.getenv("POPEYE_PATH", "popeye")
    ), singleton=False)
    
    # Register Blackboard as a singleton
    register("blackboard", 
    lambda: Blackboard(), 
    singleton=True)

    register("brave_search",
    lambda: BraveSearchTool(n_results=20),
    singleton=False)
    
    # Register StackOverflow Search Tool
    register("stackoverflow_search",
    lambda: StackOverflowSearchTool(
        brave_search=get("brave_search"),
    ),
    singleton=False)

    # Register Web Browser Tool
    register("web_browser_tool",
    lambda: WebBrowserTool(
        brave_search=get("brave_search"),
    ),
    singleton=False)


def register(name: str,
             factory: Callable[[], Any],
             *,
             singleton: bool = True,) -> None:
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
