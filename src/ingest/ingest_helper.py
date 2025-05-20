from litellm import completion
import os
from src.embeddings.late_chunking import LateChunkingHelper
from src.database.weviate import WeaviateHelper
import logging
import yaml
import traceback
import asyncio
import logging

logger = logging.getLogger(__name__)

class IngestHelper:
    """
    Helper class for ingesting and summarizing knowledge, using dependency injection for helpers.
    """
    def __init__(
        self,
        knowledge_summary_model: str,
        knowledge_config_path: str,
        override_collection: bool,
        weaviate_helper: WeaviateHelper,
        late_chunking_helper: LateChunkingHelper
    ) -> None:
        """
        Initialize IngestHelper with injected dependencies.
        """
        self.knowledge_summary_model = knowledge_summary_model
        self.knowledge_config_path = knowledge_config_path
        self.override_collection = override_collection
        self.weaviate_helper = weaviate_helper
        self.late_chunking_helper = late_chunking_helper

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

    def _scan_and_get_directories(self, dir: str, rules: dict):
        results = []
        failed_docs = []

        with os.scandir(dir) as it:
            for entry in it:
                if entry.is_dir():
                    sub_results, sub_failed = self._scan_and_get_directories(entry.path, rules)
                    results.extend(sub_results)
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
                        logger.info(f"File '{entry.path}' skipped. Reason: {skip_reason}")
                        failed_docs.append({
                            "file": entry.path,
                            "reason": skip_reason,
                            "traceback": None,
                            "summary": skip_reason
                        })
                        continue

                    try:
                        with open(entry.path, "r", encoding="utf-8") as f:
                            file_content = f.read()
                            file_length = len(file_content)
                    except Exception as e:
                        tb = traceback.format_exc()
                        reason = f"Failed to read file: {e}"
                        logger.info(f"File '{entry.path}' skipped. Reason: {reason}")
                        failed_docs.append({
                            "file": entry.path,
                            "reason": reason,
                            "traceback": tb,
                            "summary": str(e)
                        })
                        continue

                    if rules["min_length"] != -1 and file_length < rules["min_length"]:
                        reason = f"File length is {file_length} characters, which is less than the minimum length of {rules['min_length']} characters."
                        logger.info(f"File '{entry.path}' skipped. Reason: {reason}")
                        failed_docs.append({
                            "file": entry.path,
                            "reason": reason,
                            "traceback": None,
                            "summary": reason
                        })
                        continue

                    if rules["max_length"] != -1 and file_length > rules["max_length"]:
                        reason = f"File length is {file_length} characters, which is more than the maximum length of {rules['max_length']} characters."
                        logger.info(f"File '{entry.path}' skipped. Reason: {reason}")
                        failed_docs.append({
                            "file": entry.path,
                            "reason": reason,
                            "traceback": None,
                            "summary": reason
                        })
                        continue
                    
                    results.append({
                        "path": entry.path,
                        "content": file_content,
                        "file_extension": file_extension
                    })
                
        return results, failed_docs

    async def _async_generate_all_summaries(self, docs):
        semaphore = asyncio.Semaphore(10)
        loop = asyncio.get_event_loop()
        
        async def sem_task(doc):
            async with semaphore:
                return await loop.run_in_executor(None, self._generate_summary, doc["content"])
        
        return await asyncio.gather(*[sem_task(doc) for doc in docs])

    def ingest_knowledge(self):
        failed_docs = []
        config_path = self.knowledge_config_path

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        if not config or "collections" not in config:
            raise ValueError(f"Config file {self.knowledge_config_path} is empty or missing 'collections' key.")

        for collection in config["collections"]:
            with self.weaviate_helper.connect() as client:
                if client.collections.exists(collection["name"]):
                    if self.override_collection:
                        client.collections.delete(collection["name"])
                        logger.info(f"Collection '{collection['name']}' deleted.")
                    else:
                        continue
 
        for collection in config["collections"]:                
            self.weaviate_helper.create_collection(
                collection_name=collection["name"],
                description=collection["description"]
            )

            all_docs = []
            all_failed = []
            
            for dir in collection["dirs"]:
                docs, failed = self._scan_and_get_directories(dir, collection["rules"])
                all_docs.extend(docs)
                all_failed.extend(failed)

            # Separate docs that need summaries
            needs_summary = collection["rules"].get("generate_summary", False)
            docs_for_summary = all_docs if needs_summary else []
            summaries = []

            # Async summary generation if needed
            if needs_summary and docs_for_summary:
                try:
                    summaries = asyncio.run(self._async_generate_all_summaries(docs_for_summary))
                except RuntimeError:
                    summaries = asyncio.get_event_loop().run_until_complete(self._async_generate_all_summaries(docs_for_summary))
                for doc, summary in zip(docs_for_summary, summaries):
                    try:
                        doc["summary"] = summary["choices"][0]["message"]["content"]
                    except Exception as e:
                        doc["summary"] = ""
                        logger.info(f"Failed to attach summary for file '{doc['path']}': {e}")

            # Now chunk and embed
            embedded_docs = []
            for doc in all_docs:
                try:
                    # Pass summary for YAML files if present
                    summary = doc.get("summary", "") if doc["file_extension"] in ["yaml", "yml"] else ""
                    docs_chunks, canonical_doc = self.late_chunking_helper.chunk_file(doc["path"], summary=summary)
                    embedded = self.late_chunking_helper.generate_late_chunking_embeddings(docs_chunks, canonical_doc)
                    embedded_docs.extend(embedded)
                except Exception as e:
                    tb = traceback.format_exc()
                    all_failed.append({
                        "file": doc["path"],
                        "reason": f"Failed during chunking/embedding: {e}",
                        "traceback": tb,
                        "summary": str(e)
                    })
            self.weaviate_helper.batch_insert(embedded_docs, collection["name"])
            logger.info(f"Documents inserted into collection '{collection['name']}'.")

            if all_failed:
                logger.info(f"Failed to process {len(all_failed)} documents.")
            failed_docs.extend(all_failed)

        return failed_docs

                        

                        

                        

                        