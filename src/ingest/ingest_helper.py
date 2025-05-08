from litellm import completion
import os
from src.embeddings.late_chunking import LateChunkingHelper
from src.database.weviate import WeaviateHelper
import logging
import yaml
import traceback

class IngestHelper:
    def __init__(self, 
    knowledge_summary_model: str,
    knowledge_config_path: str,
    override_collection: bool,
    weaviate_helper: WeaviateHelper,
    late_chunking_helper: LateChunkingHelper,
    ):
        self.knowledge_summary_model = knowledge_summary_model
        self.knowledge_config_path = knowledge_config_path
        self.override_collection = override_collection
        self.weaviate_helper = weaviate_helper
        self.late_chunking_helper = late_chunking_helper
        self.logger = logging.getLogger(__name__)

    def _generate_summary(self, content: str):
        
        system_prompt = "You are an experienced tech teacher, specialized in DevOps and Cloud Computing."

        user_prompt = f"Your task is to generate a summary of the given content if it has theoretical content or describe in detail the code if it has code content (ensure that in case of the code a general description is added, after that, details about what the code does are added). The summary should be concise and easy to understand. Write in a maximum of paragraphs.\n\nThe content to summarize is the following, marked with <content> tags: \n\n<content>\n{content}\n</content>"
        
        return completion(
            model=self.knowledge_summary_model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            num_retries=3,
        )

    def _scan_and_embed_documents(self, dir: str, rules: dict):
        results = []
        failed_docs = []

        with os.scandir(dir) as it:
            for entry in it:
                if entry.is_dir():
                    # Recursively collect failed docs from subdirs
                    _, sub_failed = self._scan_and_embed_documents(entry.path, rules)
                    failed_docs.extend(sub_failed)
                elif entry.is_file():
                    file_extension = entry.name.split(".")[-1]
                   
                    # Check skip reasons and log them
                    skip_reason = None
                    if not rules["include"]:
                        skip_reason = "No include patterns specified."
                    elif not (file_extension in rules["include"] or "*" in rules["include"]):
                        skip_reason = f"File extension '{file_extension}' not in include list {rules['include']}"
                    elif rules["exclude"] and file_extension in rules["exclude"]:
                        skip_reason = f"File extension '{file_extension}' is in exclude list {rules['exclude']}"

                    if skip_reason:
                        self.logger.info(f"File '{entry.path}' skipped. Reason: {skip_reason}")
                        failed_docs.append({
                            "file": entry.path,
                            "reason": skip_reason,
                            "traceback": None,
                            "summary": skip_reason
                        })
                        continue

                    file_length = 0
                    file_content = ""
                    try:
                        with open(entry.path, "r", encoding="utf-8") as f:
                            file_length = len(f.read())
                            file_content = f.read()
                    except Exception as e:
                        tb = traceback.format_exc()
                        reason = f"Failed to read file: {e}"
                        self.logger.info(f"File '{entry.path}' skipped. Reason: {reason}")
                        failed_docs.append({
                            "file": entry.path,
                            "reason": reason,
                            "traceback": tb,
                            "summary": str(e)
                        })
                        continue

                    if rules["min_length"] != -1 and file_length < rules["min_length"]:
                        reason = f"File length is {file_length} characters, which is less than the minimum length of {rules['min_length']} characters."
                        self.logger.info(f"File '{entry.path}' skipped. Reason: {reason}")
                        failed_docs.append({
                            "file": entry.path,
                            "reason": reason,
                            "traceback": None,
                            "summary": reason
                        })
                        continue
                    if rules["max_length"] != -1 and file_length > rules["max_length"]:
                        reason = f"File length is {file_length} characters, which is more than the maximum length of {rules['max_length']} characters."
                        self.logger.info(f"File '{entry.path}' skipped. Reason: {reason}")
                        failed_docs.append({
                            "file": entry.path,
                            "reason": reason,
                            "traceback": None,
                            "summary": reason
                        })
                        continue

                    try:
                        docs, canonical_doc = self.late_chunking_helper.chunk_file(entry.path)
                        summary = ""
                        if rules["generate_summary"]:
                            summary = self._generate_summary(file_content)
                            summary = summary["choices"][0]["message"]["content"]  
                            self.logger.info(f"Summary generated for file '{entry.path}'.")
                        docs = self.late_chunking_helper.generate_late_chunking_embeddings(docs, canonical_doc)
                        results.extend(docs)
                        self.logger.info(f"{len(docs)} documents generated for file '{entry.path}'.")
                    except Exception as e:
                        tb = traceback.format_exc()
                        reason = f"Failed to process file: {e}"
                        self.logger.info(f"File '{entry.path}' skipped during processing. Reason: {reason}")
                        failed_docs.append({
                            "file": entry.path,
                            "reason": reason,
                            "traceback": tb,
                            "summary": str(e)
                        })
                        continue
        return results, failed_docs

    def ingest_knowledge(self):
        failed_docs = []
        config = self.knowledge_config_path

        for collection in config["collections"]:
            with self.weaviate_helper.connect() as client:
                if client.collections.exists(collection["name"]):
                    if self.override_collection:
                        client.collections.delete(collection["name"])
                        self.logger.info(f"Collection '{collection['name']}' deleted.")
                    else:
                        continue

        with open(config, "r") as f:
            config = yaml.safe_load(f)       

        for collection in config["collections"]:                
            self.weaviate_helper.create_collection(
                collection_name=collection["name"], 
                description=collection["description"]
            )

            for dir in collection["dirs"]:
                docs, failed_docs = self._scan_and_embed_documents(dir, collection["rules"])
                failed_docs.extend(failed_docs)
                self.weaviate_helper.batch_insert(docs, collection["name"])
                self.logger.info(f"Documents inserted into collection '{collection['name']}'.")

            if failed_docs:
                self.logger.info(f"Failed to process {len(failed_docs)} documents.")

        return failed_docs

                        

                        

                        

                        