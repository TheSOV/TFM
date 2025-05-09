"""
ingest_knowledge.py
-------------------

This script is the entry point for ingesting knowledge documents into the Weaviate vector database.

How it works:
- Loads environment variables (such as API keys and configuration paths) using dotenv.
- Sets up logging for informative output.
- Initializes the dependency injection container, which manages components like the ingest helper and database connections.
- Creates an instance of the IngestHelper, which contains the logic for scanning directories, filtering and reading files, generating summaries (if needed), embedding content, and inserting documents into Weaviate collections.
- Calls `ingest_helper.ingest_knowledge()`, which:
    - Reads the configuration from `config/knowledge/knowledge.yaml` to determine which collections, directories, and file types to ingest.
    - Recursively scans the specified directories, applies include/exclude rules, and reads file contents.
    - Optionally generates summaries for documents, if configured.
    - Embeds the content using the specified embedding model.
    - Inserts the processed documents into the appropriate Weaviate collections.
    - Returns a list of failed documents (if any) for troubleshooting.

Usage:
- Run this script directly to trigger the knowledge ingestion pipeline. Make sure your environment variables and YAML config are set up correctly.
- The script can be used as a standalone command-line tool or imported as a module if needed.
"""

from dotenv import load_dotenv
from src.containers import Container
import logging

logging.basicConfig(level=logging.INFO)
load_dotenv()   
container = Container()

ingest_helper = container.ingest_helper()
failed_docs = ingest_helper.ingest_knowledge()

print(failed_docs)