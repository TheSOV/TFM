# containers.py
from dependency_injector import containers, providers
from src.embeddings.late_chunking import LateChunkingHelper
from src.database.weviate import WeaviateHelper

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

        # ---------- load defaults / env overrides ----------
    # This runs once when the module is imported
    config.late_chunking_helper.model_name.from_env("LATE_CHUNKING_MODEL_NAME", "jinaai/jina-embeddings-v3")
    config.late_chunking_helper.headers_to_split_on.from_env("LATE_CHUNKING_HEADERS_TO_SPLIT_ON", "[(\"#\", \"h1\"), (\"##\", \"h2\")]")
    config.late_chunking_helper.max_chunk_chars.from_env("LATE_CHUNKING_MAX_CHUNK_CHARS", 2048)
    config.late_chunking_helper.device.from_env("LATE_CHUNKING_DEVICE", "cpu")
    config.weaviate_helper.weaviate_api_key.from_env("WEAVIATE_API_KEY")
    config.weaviate_helper.weaviate_host.from_env("WEAVIATE_HOST", "127.0.0.1")
    config.weaviate_helper.weaviate_port.from_env("WEAVIATE_PORT", "8080")
    config.weaviate_helper.weaviate_grpc_port.from_env("WEAVIATE_GRPC_PORT", "50051")

    late_chunking_helper = providers.Singleton(
        LateChunkingHelper,
        model_name=config.late_chunking_helper.model_name,
        headers_to_split_on=config.late_chunking_helper.headers_to_split_on,
        max_chunk_chars=config.late_chunking_helper.max_chunk_chars.as_int(),
        device=config.late_chunking_helper.device,
    )
    weaviate_helper = providers.Singleton(WeaviateHelper,
                                   weaviate_api_key=config.weaviate_helper.weaviate_api_key,
                                   weaviate_host=config.weaviate_helper.weaviate_host,
                                   weaviate_port=config.weaviate_helper.weaviate_port,
                                   weaviate_grpc_port=config.weaviate_helper.weaviate_grpc_port)
