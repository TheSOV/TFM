from typing import Callable, Any, Dict, Tuple
import os

from src.embeddings.late_chunking import LateChunkingHelper
from src.database.weviate import WeaviateHelper
from src.ingest.ingest_helper import IngestHelper

from src.crewai.tools.file_edit_tool import FileCreateTool, FileEditTool, FileReadTool  
from src.crewai.tools.config_validator import ConfigValidatorTool

from src.crewai.tools.rag_tool import RagTool


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

    register("file_create", 
    lambda: FileCreateTool(
        base_dir=os.getenv("TEMP_FILES_DIR")
    ), singleton=False)

    register("file_edit", 
    lambda: FileEditTool(
        base_dir=os.getenv("TEMP_FILES_DIR")
    ), singleton=False)

    register("file_read", 
    lambda: FileReadTool(
        base_dir=os.getenv("TEMP_FILES_DIR")
    ), singleton=False)

    register("config_validator", 
    lambda: ConfigValidatorTool(
        base_dir=os.getenv("TEMP_FILES_DIR")
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



