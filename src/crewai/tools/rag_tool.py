from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from src.database.weviate import WeaviateHelper
from src.embeddings.late_chunking import LateChunkingHelper
from pydantic import PrivateAttr
from typing import Optional

class RagToolInput(BaseModel):
    """Input schema for MyCustomTool."""
    query: str = Field(..., description="Query to search in the knowledge base.")
    collection: str = Field(..., description="Collection to search in.")
    retrieve_limit: Optional[int] = Field(25, description="Limit of results to initial retrieve, before reranking.")
    rerank_limit: Optional[int] = Field(10, description="Limit of results to return after reranking. This is the final number of results returned by the tool.")

class RagTool(BaseTool):
    """
    Tool for Retrieval-Augmented Generation (RAG) using Weaviate and LateChunking helpers.
    Uses dependency injection for its dependencies.
    The description is dynamically generated based on available collections.
    """
    name: str = "rag_tool"
    args_schema: Type[BaseModel] = RagToolInput
    description: Optional[str] = None

    _weaviate_helper: WeaviateHelper = PrivateAttr()
    _late_chunking_helper: LateChunkingHelper = PrivateAttr()

    def __init__(
        self,
        weaviate_helper: WeaviateHelper,
        late_chunking_helper: LateChunkingHelper,
        **kwargs
    ) -> None:
        """
        Initialize the RAG tool with injected dependencies (via DI or direct),
        and set a dynamic description based on available Weaviate collections.
        Always sets PrivateAttr fields after calling super().__init__.
        """
        super().__init__(**kwargs)
        self._weaviate_helper = weaviate_helper
        self._late_chunking_helper = late_chunking_helper

        # Set dynamic description if helpers are available
        desc = "The rag_tool is used to search in the knowledge base. Specify the query and the collection to search in. "
        if self._weaviate_helper is not None:
            try:
                collections = []
                with self._weaviate_helper.connect() as client:
                    for collection_name in client.collections.list_all():
                        collection = client.collections.get(collection_name)
                        config = collection.config.get(True)
                        collections.append({"name": collection_name, "description": config.description})
                desc += "The collection name must match the name in Weaviate.\n"
                for collection in collections:
                    desc += f"Collection name: {collection['name']}, description: {collection['description']}\n"
            except Exception:
                desc += "(Could not retrieve collections at initialization.)"
        else:
            desc += "(Weaviate helper not available at initialization.)"
        self.description = desc

    def _run(self, query: str, collection: str, retrieve_limit: int = 25, rerank_limit: int = 10) -> str:
        """
        Run a RAG query using the injected helpers.

        Args:
            query (str): The search query.
            collection (str): The collection to search in.
            retrieve_limit (int): Number of documents to retrieve before reranking.
            rerank_limit (int): Number of documents to return after reranking.

        Returns:
            str: The reranked documents or result string.
        """
        query_embedding = self._late_chunking_helper.generate_query_embedding(query)
        retrieved_docs = self._weaviate_helper.rag_query(collection, query_embedding, limit=retrieve_limit)

        docs = [doc.properties for doc in retrieved_docs]

        reranked_docs = self._late_chunking_helper.re_rank(query = query, docs = docs, top_k = rerank_limit)
        return reranked_docs


