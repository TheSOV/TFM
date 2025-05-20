import logging
import os
import weaviate
import numpy as np
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure
from weaviate.classes.data import DataObject
from weaviate.util import generate_uuid5

logger = logging.getLogger(__name__)

class WeaviateHelper:
    def __init__(self, weaviate_api_key: str, weaviate_host: str, weaviate_port: str, weaviate_grpc_port: str):
        # Best practice: store your credentials in environment variables
        self.weaviate_api_key = weaviate_api_key
        self.weaviate_host = weaviate_host
        self.weaviate_port = weaviate_port
        self.weaviate_grpc_port = weaviate_grpc_port

    def connect(self):
        return weaviate.connect_to_local(
            auth_credentials=Auth.api_key(self.weaviate_api_key),
            host=self.weaviate_host,
            port=self.weaviate_port,    
            grpc_port=self.weaviate_grpc_port,
        )

    def create_collection(self, collection_name: str, description: str):
        with self.connect() as client:
            if not client.collections.exists(collection_name):
                client.collections.create(
                    name=collection_name,
                    description=description,
                    vectorizer_config=Configure.Vectorizer.none(),
                )
                logger.info(f"Collection '{collection_name}' created.")
            else:
                logger.info(f"Collection '{collection_name}' already exists.")

    def batch_insert(self, docs: list[dict], collection_name: str):
        with self.connect() as client:

            if not client.collections.exists(collection_name):
                raise ValueError(f"Collection '{collection_name}' not found.")

            collection = client.collections.get(name=collection_name)
            
            to_insert = []
            for doc in docs:
                # extract and flatten embedding vector
                raw_meta = doc["late_chunking_metadata"]
                vec = np.asarray(raw_meta["embedding"]).reshape(-1).tolist()
                # build properties by excluding raw metadata
                props = {k: v for k, v in doc.items() if k != "late_chunking_metadata"}

                # Generate a UUID5 based on the document content
                uuid_prop = {"filename": doc["filename"], "content": doc["content"]}
                uuid = generate_uuid5(uuid_prop)

                to_insert.append(DataObject(
                    properties=props,
                    vector=vec,
                    uuid=uuid,
                ))

            collection.data.insert_many(to_insert)

    def rag_query(self, collection_name: str, query_embedding: list[float], limit: int = 50):
        with self.connect() as client:
            if not client.collections.exists(collection_name):
                raise ValueError(f"Collection '{collection_name}' not found.")

            collection = client.collections.get(name=collection_name)

            # Flatten any nested structure to a 1D list for Weaviate
            vec = np.asarray(query_embedding).reshape(-1).tolist()
            results = collection.query.near_vector(
                near_vector=vec,
                limit=limit
            )

            return results.objects