# KubernetesCrew

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/TheSOV/TFM)


# TFM - AI-Powered DevOps Automation System

The repository contains a DevOps automation assistant that leverages AI agents, vector databases, and comprehensive tooling to streamline infrastructure management and operations, designed for Kubernetes as part of the final project of my Master's Thesis in Applied Artificial Intelligence. This is repo is indexed with DeepWiki, you can ask questions about it [here](https://deepwiki.com/TheSOV/TFM).

## Features

- **AI Agent Crews**: Powered by CrewAI for task automation
- **Knowledge Management**: Vector-based RAG system using Weaviate
- **File Operations**: File editing with version control integration
- **Web Research**: Web browsing and information extraction
- **Container Analysis**: Docker image analysis and registry search
- **Kubernetes Integration**: Safe kubectl operations
- **Security Scanning**: Built-in security validation tools

## Prerequisites

- Python 3.10.x - 3.11.x (Python 3.12+ not supported) 
- Docker & Docker Compose
- Kind
- Poetry
- Popeye
- 8GB+ RAM (16GB+ recommended)
- Internet access
- Download the knowlegde (available in [here](https://1drv.ms/f/c/d94c004a66a13a4a/EmBMizQa_PNBr0sqjnmccFMBEUKG0djnbNecYOaT5Mvlug?e=YJqhgS)) and copy it to knowledge folder or create and configure your own

## Quick Start

### 1. Environment Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/TheSOV/TFM
cd TFM
poetry install
```

### 2. Configuration

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

#### AI/LLM Configuration
```bash
# OpenAI API (required for AI agents)
OPENAI_API_KEY=your_openai_api_key_here

# Alternative: OpenRouter API/ In roadmap
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

# Model Configuration
AGENT_MAIN_MODEL="openai/gpt-4.1-mini" # model that will be used by the agents during reasoning and to answer the user
AGENT_TOOL_CALL_MODEL="openai/gpt-4.1-mini" # model that will be used by the agents during tool calls
TOOL_MODEL="openai/gpt-4.1-mini" # model that will be used by the tools (in most case, to summarize raw information gathered by the RAG and Web Research tools)
GUARDRAIL_MODEL="openai/gpt-4.1-nano" # model that will be used by the guardrails (to validate the agents' responses)
```

#### Vector Database Configuration
```bash
# Weaviate Vector Database
WEAVIATE_API_KEY=your_secure_weaviate_key
WEAVIATE_HOST="127.0.0.1"
WEAVIATE_PORT="8080"
WEAVIATE_GRPC_PORT="50051"
``` 

#### Knowledge Management
```bash
# Embedding Model Configuration
LATE_CHUNKING_MODEL_NAME="jinaai/jina-embeddings-v3" # model that will be used to generate embeddings for the knowledge
LATE_CHUNKING_HEADERS_TO_SPLIT_ON=[("#", "h1"), ("##", "h2")] # headers to split on for markdown files
LATE_CHUNKING_MAX_CHUNK_CHARS=2048 # maximum chunk size in characters
LATE_CHUNKING_DEVICE="cuda"  # or "cpu", "cuda" is recommended for GPU acceleration

# Knowledge Ingestion
INGEST_KNOWLEDGE_SUMMARY_MODEL="gpt-4.1-nano" # model that will be used to generate summaries for the knowledge
INGEST_KNOWLEDGE_CONFIG_PATH="config/knowledge/knowledge.yaml" # path to the knowledge ingestion configuration file
INGEST_KNOWLEDGE_OVERRIDE_COLLECTION=True # override the collection if it already exists. When this option is enabled, the ingestion process will check at the begining if the collection already exists and if it does, it will be deleted and recreated. This verification occurs before the ingestion process starts, if multiple knowledge sources are configured with the same collection name, they will still be merged.
``` 

#### File System Configuration
```bash
# Working Directories
TEMP_FILES_DIR="temp" # directory where the kubernetes YAML files will be stored during the assistant's execution
CONFIG_FILES_DIR="config" # directory where configuration files are stored
CREWAI_STORAGE_DIR="./memory" # directory where CrewAI will store its memory (on roadmap)
``` 

#### Kubernetes Configuration
```bash
# kubectl Setup
KUBECTL_PATH="kubectl"  # or full path on Windows
KUBECTL_ALLOWED_VERBS="get,describe,logs,apply,diff,delete,create,patch,exec,cp,rollout,scale" # verbs allowed to be used by the assistant
KUBECTL_SAFE_NAMESPACES=""  # comma-separated list of all safe namespaces, leave empty to allow all namespaces
KUBECTL_DENIED_NAMESPACES="kube-system,kube-public" # comma-separated list of all denied namespaces
KUBECTL_DENY_FLAGS="--raw,--kubeconfig,--context,-ojsonpath,--output" # comma-separated list of all denied flags
K8S_VERSION="v1.29.0" # kubernetes version targeted
``` 

#### External API Keys
```bash
# Web Research APIs
STACK_EXCHANGE_API_KEY=your_stack_exchange_key # stack exchange API key
BRAVE_API_KEY=your_brave_search_key # brave search API key
```

#### Security Tools
```bash
POPEYE_PATH="/path/to/popeye"  # Kubernetes cluster scanner
``` 

## Configure knowledge sources and ingestion
The `config/knowledge/knowledge.yaml` file, defines how knowledge ingestion system processes documents for the RAG (Retrieval Augmented Generation) system. The `knowledge.yaml` file defines collections of documents that will be ingested into the Weaviate vector database. 

## Collection Configuration

Each collection in the YAML file must have the following structure:

- **`name`**: The Weaviate collection identifier. If you use the same name for multiple collections, they will be merged into a single collection. If you use different names, they will be created as separate collections. While using RAG system, the collections will isolate the information, forcing to make a query over one collection at a time.
- **`description`**: Metadata describing the collection's content. It is useful when multiple collections are defined, allowing the assistant to know what information a collection contains.  
- **`dirs`**: List of directories to scan for documents. Directories are scaned recursively.
- **`rules`**: Processing rules for file filtering and handling 

## Processing Rules

The `rules` section controls how files are processed during ingestion:

### File Filtering Rules

- **`include`**: Array of file extensions to process (e.g., `["md"]`, `["yaml", "yml"]`, `["adoc"]`)
- **`exclude`**: Array of file extensions to skip (typically empty `[]`)
- **`min_length`**: Minimum file size in characters (`-1` for unlimited)
- **`max_length`**: Maximum file size in characters (`-1` for unlimited)

### Summary Generation

- **`generate_summary`**: Boolean flag controlling whether to generate LLM summaries, that will be added as a comment at the beginning of the file. 
  - Set to `true` for code only files to add context 
  - Set to `false` for files that are self-documenting 

## File Type Processing

The ingestion system handles different file types with specialized chunking strategies:

### Markdown Files
- Uses header-aware chunking with `MarkdownHeaderTextSplitter`
- Preserves document structure through header hierarchy
- No summary generation needed (self-documenting)

### YAML Files  
- Prepends generated summary as a comment 
- Treats entire file as single chunk
- Requires `generate_summary: true` for context

### Other Files
- Uses generic recursive character splitting
- Falls back to standard chunking strategy


## Example Configuration

Here's how to configure a new knowledge source:

```yaml
collections:
  - name: "knowledge"
    description: "Custom documentation collection about Kubernetes"
    dirs:
      - "knowledge\\custom\\docs"
      - "knowledge\\custom\\docs2"
    rules:
      include: ["md", "rst"]
      exclude: []
      min_length: 100
      max_length: -1
      generate_summary: false
```

The ingestion process will scan the specified directories, apply the filtering rules, and process matching files according to their type-specific chunking strategy before storing them in the Weaviate vector database. To begin the ingestion process, run the [ingest_knowledge.py](ingest_knowledge.py) script.

## CUDA Support (recommended)

For CUDA support (GPU acceleration):

```bash
poetry install --with cu118
``` 

### 3. Usage

To run the application, execute:

```bash
python main.py
```

