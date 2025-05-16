# containers.py
from dependency_injector import containers, providers
from src.embeddings.late_chunking import LateChunkingHelper
from src.database.weviate import WeaviateHelper
from src.ingest.ingest_helper import IngestHelper
from src.crewai.tools.yaml_editor_tools import YamlCreateTool, YamlEditTool, YamlReadTool

from src.crewai.tools.rag_tool import RagTool

import ast

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Base directory for all YAML tool file operations
    config.temp_files_dir.from_env("TEMP_FILES_DIR", default="temp")

    # ---------- load defaults / env overrides ----------
    # This runs once when the module is imported
    config.late_chunking_helper.model_name.from_env("LATE_CHUNKING_MODEL_NAME", "jinaai/jina-embeddings-v3")
    config.late_chunking_helper.headers_to_split_on.from_env("LATE_CHUNKING_HEADERS_TO_SPLIT_ON", "[(\"#\", \"h1\"), (\"##\", \"h2\")]")
    config.late_chunking_helper.max_chunk_chars.from_env("LATE_CHUNKING_MAX_CHUNK_CHARS", as_=int, default=2048)
    config.late_chunking_helper.device.from_env("LATE_CHUNKING_DEVICE", "cpu")
        
    config.weaviate_helper.weaviate_api_key.from_env("WEAVIATE_API_KEY")
    config.weaviate_helper.weaviate_host.from_env("WEAVIATE_HOST", "127.0.0.1")
    config.weaviate_helper.weaviate_port.from_env("WEAVIATE_PORT", "8080")
    config.weaviate_helper.weaviate_grpc_port.from_env("WEAVIATE_GRPC_PORT", "50051")

    config.ingest_helper.knowledge_summary_model.from_env("INGEST_KNOWLEDGE_SUMMARY_MODEL", "gpt-4.1-nano")
    config.ingest_helper.knowledge_config_path.from_env("INGEST_KNOWLEDGE_CONFIG_PATH", "config/knowledge/knowledge.yaml")
    config.ingest_helper.override_collection.from_env("INGEST_KNOWLEDGE_OVERRIDE_COLLECTION", as_=ast.literal_eval, default="True")

    late_chunking_helper = providers.Singleton(LateChunkingHelper,
                                    model_name=config.late_chunking_helper.model_name,
                                    headers_to_split_on=config.late_chunking_helper.headers_to_split_on,
                                    max_chunk_chars=config.late_chunking_helper.max_chunk_chars,
                                    device=config.late_chunking_helper.device,
    )
    weaviate_helper = providers.Singleton(WeaviateHelper,
                                   weaviate_api_key=config.weaviate_helper.weaviate_api_key,
                                   weaviate_host=config.weaviate_helper.weaviate_host,
                                   weaviate_port=config.weaviate_helper.weaviate_port,
                                   weaviate_grpc_port=config.weaviate_helper.weaviate_grpc_port)

    ingest_helper = providers.Singleton(IngestHelper,
                                   knowledge_summary_model=config.ingest_helper.knowledge_summary_model,
                                   knowledge_config_path=config.ingest_helper.knowledge_config_path,
                                   override_collection=config.ingest_helper.override_collection,
                                   weaviate_helper=weaviate_helper,
                                   late_chunking_helper=late_chunking_helper)


    # RAG tool for CrewAI agents
    rag_tool = providers.Factory(RagTool)

    # YAML editor tools for CrewAI agents, passing base_dir from config
    yaml_create_tool = providers.Factory(YamlCreateTool, base_dir=config.temp_files_dir)
    yaml_edit_tool = providers.Factory(YamlEditTool, base_dir=config.temp_files_dir)
    yaml_read_tool = providers.Factory(YamlReadTool, base_dir=config.temp_files_dir)
