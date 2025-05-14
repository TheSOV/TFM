from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from src.containers import WeaviateHelper
from src.containers import LateChunkingHelper

class RagToolInput(BaseModel):
    """Input schema for MyCustomTool."""
    query: str = Field(..., description="Query to search in the knowledge base.")
    collection: str = Field(..., description="Collection to search in.")
    retrieve_limit: int = Field(..., description="Limit of results to initial retrieve, before reranking.")
    rerank_limit: int = Field(..., description="Limit of results to return after reranking. This is the final number of results returned by the tool.")

class RagTool(BaseTool):
    name: str = "RAG Tool"    
    args_schema: Type[BaseModel] = RagToolInput

    def __init__(self, weaviate_helper: WeaviateHelper, late_chunking_helper: LateChunkingHelper):
        self.weaviate_helper = weaviate_helper
        self.late_chunking_helper = late_chunking_helper

        collections = []

        # Get all collections names and descriptions
        with self.weaviate_helper.connect() as client:
            for collection_name in client.collections.list_all():
                collection = client.collections.get(collection_name)
                config = collection.config.get(True)
                collections.append({"name": collection_name, "description": config.description})

        # Build description
        self.description: str = "Tool to search in the knowledge base to use it, you need to specify the query and the collection to search in. The name of the collection must match the name of the collection in weaviate, which are the ones listed below one per line, in the format: Collection name: <name>, description: <description>:"
        for collection in collections:
            self.description += f"\nCollection name: {collection['name']}, description: {collection['description']}"  

    def _run(self, query: str, collection: str, retrieve_limit: int = 25, rerank_limit: int = 10) -> str:
        query_embedding = self.late_chunking_helper.generate_query_embedding(query)
        retrieved_docs = self.weaviate_helper.rag_query(collection, query_embedding, limit=retrieve_limit)
        reranked_docs = self.late_chunking_helper.re_rank(retrieved_docs, query, rerank_limit)
        return reranked_docs