"""
CrewAI-ready Tool wrappers for the YAML helpers above.
Mix & match: either subclass BaseTool *or* use the @tool decorator.
"""
from typing   import Any, Dict, List, Literal, Optional, Type, Union
from pydantic import BaseModel, Field, PrivateAttr, field_validator, ValidationInfo
from crewai.tools import BaseTool, tool
import io
import json, pathlib
from textwrap import dedent

import src.crewai.tools.utils.yaml_toolkit as yt  # <-- import the low-level helpers

# ------------------------------------------------------------------
# 1) CLASS-BASED TOOLS  (offer fine-grained control & easy unit-tests)
# ------------------------------------------------------------------
class _YAMLReadArgs(BaseModel):
    document_index: Optional[int] = Field(None, description="Optional: The index of a specific document to read. If not provided, all documents are read.")

class YAMLReadTool(BaseTool):
    name        : str               = "read_yaml"
    description : str               = "Load a YAML file and return its content as a JSON string."
    args_schema : Type[BaseModel]   = _YAMLReadArgs
    _file_path: pathlib.Path = PrivateAttr()

    def __init__(self, file_path: Union[str, pathlib.Path], **kwargs):
        super().__init__(**kwargs)
        self._file_path = pathlib.Path(file_path)
        self.description = (
            f"A tool to read content from the YAML file at '{self._file_path}'. "
            "The file path is set during initialization. It can read all documents from a multi-document file "
            "(returning a list of indexed documents) or a single document by specifying its index."
        )

    def _run(self, document_index: Optional[int] = None) -> str:
        try:

            p_path = self._file_path
            if not p_path.exists():
                return f"Error: File not found at {p_path}"

            yaml = yt.get_yaml_instance()
            docs = list(yaml.load_all(p_path))

            if document_index is None:
                # Read all documents and return them with their indices
                indexed_docs = [{"index": i, "document": doc} for i, doc in enumerate(docs)]
                return json.dumps(indexed_docs, indent=2)
            else:
                # Read a specific document
                if document_index < 0 or document_index >= len(docs):
                    return f"Error: Document index {document_index} is out of bounds for a file with {len(docs)} documents."
                return json.dumps(docs[document_index], indent=2)

        except Exception as e:
            return f"Error reading YAML file: {e}"


class YAMLOperation(BaseModel):
    """
    Model for a key-specific operation in a YAML file.
    """
    operation: Literal["add", "replace", "delete", "add_document", "delete_document"] = Field(..., description="Operation type: 'add', 'replace', 'delete', 'add_document', or 'delete_document'")
    key: Optional[str] = Field(None, description="Dot-separated path for key-based operations (e.g., 'a.b.c'). Not used for 'add_document'.")
    value: Optional[Any] = Field(
        None,
        description=(
            "Value for 'add' or 'replace' operations. Can be a simple value, a list, or a dictionary. "
            "Required for 'add' and 'replace'. Must be None for 'delete'."
        )
    )
    document_index: int = Field(0, description="The index of the YAML document to operate on (for multi-document files).")

    @field_validator('value', 'key')
    def validate_fields_based_on_operation(cls, v: Any, info: 'ValidationInfo'):
        op = info.data.get('operation')
        field_name = info.field_name

        if op == 'add_document':
            if field_name == 'value' and v is None:
                raise ValueError("A 'value' (the document content) is required for 'add_document'.")
            if field_name == 'key' and v is not None:
                raise ValueError("A 'key' must not be provided for 'add_document'.")
        
        elif op in ('add', 'replace'):
            if field_name == 'value' and v is None:
                raise ValueError(f"A 'value' is required for '{op}' operations.")
            if field_name == 'key' and v is None:
                raise ValueError(f"A 'key' is required for '{op}' operations.")

        elif op == 'delete':
            if field_name == 'value' and v is not None:
                raise ValueError("A 'value' must not be provided for 'delete' operations.")
            if field_name == 'key' and v is None:
                raise ValueError("A 'key' is required for 'delete' operations.")
        
        return v

class YAMLEditRequest(BaseModel):
    """
    Request model for editing an existing YAML file.
    """
    operations: List[YAMLOperation] = Field(..., description="List of key-specific operations to perform.")
    comment: str = Field(
        "Default comment: applying YAML edits.",
        description="Optional comment for version control commit message."
    )

class YAMLEditTool(BaseTool):
    name: str = "yaml_edit"
    description: str = "Edits a specific YAML file by adding, replacing, or deleting keys."
    args_schema: Type[BaseModel] = YAMLEditRequest
    _file_path: pathlib.Path = PrivateAttr()

    def __init__(self, file_path: Union[str, pathlib.Path], **kwargs):
        super().__init__(**kwargs)
        self._file_path = pathlib.Path(file_path)
        self.description = dedent(f"""\
            A powerful tool to create and edit the YAML file at '{self._file_path}'.
            The file path is set during initialization. It creates the file if it doesn't exist.
            It supports five operations: 'add' (a new key), 'replace' (an existing key), 'delete' (a key), 'add_document' (appends a new document), and 'delete_document' (removes a document by index).
            All operations preserve comments and formatting.

            **HOW TO USE:**
            Provide a list of `operations`.
            - For key-based changes ('add', 'replace', 'delete'), specify 'key', 'operation', 'value', and a 'document_index' (default is 0, but the index of the document to edit must be added to make it work properly).
            - For adding a new document, use the 'add_document' operation and provide the document content in 'value'. This operation always appends the new document to the end of the file, so any 'document_index' provided for it is ignored.

            **EXAMPLES:**

            **1. Create a file and add two documents:**
               ```json
               {{
                 "operations": [
                   {{ "operation": "add_document", "value": {{"server": {{"host": "localhost"}} }} }},
                   {{ "operation": "add_document", "value": {{"database": {{"user": "admin"}} }} }}
                 ]
               }}
               ```

            **2. Edit an existing document and add a new one:**
               ```json
               {{
                 "operations": [
                   {{ "key": "server.host", "operation": "replace", "value": "app.prod.com", "document_index": 0 }},
                   {{ "operation": "add_document", "value": {{"features": {{"new_ui": true}} }} }}
                 ]
               }}
               ```

            **3. Add a new key and delete another:**
               ```json
               {{
                 "operations": [
                   {{ "key": "database.port", "operation": "add", "value": 5433, "document_index": 1 }},
                   {{ "key": "server.obsolete_flag", "operation": "delete", "document_index": 0 }}
                 ]
               }}
               ```

            **4. Add a complex dictionary object:**
               ```json
               {{
                 "operations": [
                   {{ "key": "server.tls", "operation": "add", "value": {{"enabled": true, "cert_path": "/etc/ssl/cert.pem"}} }}
                 ]
               }}
               ```
        """)

    def _run(self, operations: List[Dict[str, Any]], comment: str) -> str:
        p_path = self._file_path
        yaml = yt.get_yaml_instance()

        try:
            if p_path.exists():
                docs = list(yaml.load_all(p_path))
            else:
                docs = []

            # Build a map of existing Kubernetes resources to detect duplicates.
            # The key is (apiVersion, kind, name, namespace), value is a dict with original index and content.
            existing_resources = {}
            for i, doc in enumerate(docs):
                if isinstance(doc, dict) and all(k in doc for k in ["apiVersion", "kind", "metadata"]):
                    metadata = doc.get('metadata', {})
                    if isinstance(metadata, dict) and 'name' in metadata:
                        api_version = doc.get('apiVersion')
                        kind = doc.get('kind')
                        name = metadata.get('name')
                        namespace = metadata.get('namespace')  # Can be None
                        resource_key = (api_version, kind, name, namespace)
                        if resource_key not in existing_resources:
                            existing_resources[resource_key] = {"index": i, "content": doc}

            # Process 'delete_document' operations first to avoid index shifting issues.
            delete_doc_indices = sorted([op['document_index'] for op in operations if op.get('operation') == 'delete_document'], reverse=True)
            for index in delete_doc_indices:
                if index < len(docs):
                    del docs[index]
                else:
                    raise IndexError(f"Cannot delete document at index {index}: file only has {len(docs)} documents.")

            # Process 'add_document' operations next, checking for duplicates.
            add_doc_ops = [YAMLOperation(**op) for op in operations if op.get('operation') == 'add_document']
            for op in add_doc_ops:
                new_doc = op.value
                if isinstance(new_doc, dict) and all(k in new_doc for k in ["apiVersion", "kind", "metadata"]):
                    metadata = new_doc.get('metadata', {})
                    if isinstance(metadata, dict) and 'name' in metadata:
                        api_version = new_doc.get('apiVersion')
                        kind = new_doc.get('kind')
                        name = metadata.get('name')
                        namespace = metadata.get('namespace')
                        resource_key = (api_version, kind, name, namespace)

                        if resource_key in existing_resources:
                            existing_info = existing_resources[resource_key]
                            error_msg = (
                                f"Cannot add duplicate manifest. A resource with kind '{kind}' and name '{name}'"
                            )
                            if namespace:
                                error_msg += f" in namespace '{namespace}'"
                            error_msg += (
                                f" already exists at document index {existing_info['index']}.\n"
                                f"Existing resource content:\n{json.dumps(existing_info['content'], indent=2)}"
                            )
                            raise ValueError(error_msg)

                        # Add to map to prevent adding duplicates from the same request batch
                        existing_resources[resource_key] = {"index": len(docs), "content": new_doc}
                
                docs.append(op.value)

            # Group other operations by document index
            ops_by_doc = {}
            key_based_ops = [op for op in operations if op.get('operation') not in ['add_document', 'delete_document']]
            for op_data in key_based_ops:
                op = YAMLOperation(**op_data)
                if op.document_index not in ops_by_doc:
                    ops_by_doc[op.document_index] = []
                ops_by_doc[op.document_index].append(op)

            # Process operations for each document
            for doc_index, doc_ops in ops_by_doc.items():
                if doc_index >= len(docs):
                    raise IndexError(f"Cannot access document at index {doc_index}: file only has {len(docs)} documents.")
                
                for op in doc_ops:
                    if op.operation in ['add_document', 'delete_document']:
                        continue

                    if not op.key:
                        raise ValueError("The 'key' must be provided for 'add', 'replace', or 'delete' operations.")

                    parent_ref = docs[doc_index]
                    keys = op.key.split('.')
                    
                    # Traverse the path to find the parent of the target key
                    for key_part in keys[:-1]:
                        try:
                            index = int(key_part)
                            parent_ref = parent_ref[index]
                        except (ValueError, TypeError):
                            if not isinstance(parent_ref, dict):
                                raise KeyError(f"Invalid key path '{op.key}'. Cannot use string key '{key_part}' on a non-dict.")
                            parent_ref = parent_ref[key_part]
                        except IndexError:
                            raise IndexError(f"Invalid index '{key_part}' in key path '{op.key}'")
                        except KeyError:
                            raise KeyError(f"Invalid key '{key_part}' in key path '{op.key}'")

                    target_key_part = keys[-1]

                    try:
                        target_index = int(target_key_part)
                        if not isinstance(parent_ref, list):
                            raise KeyError(f"Invalid key path '{op.key}'. Cannot use index '{target_index}' on a non-list.")

                        if op.operation == 'replace':
                            if target_index >= len(parent_ref):
                                raise IndexError(f"Index {target_index} is out of bounds for list in key '{op.key}'.")
                            parent_ref[target_index] = op.value
                        elif op.operation == 'delete':
                            if target_index >= len(parent_ref):
                                raise IndexError(f"Index {target_index} is out of bounds for list in key '{op.key}'.")
                            del parent_ref[target_index]
                        elif op.operation == 'add':
                            parent_ref.insert(target_index, op.value)

                    except ValueError:
                        target_key = target_key_part
                        if not isinstance(parent_ref, dict):
                            raise KeyError(f"Invalid key path '{op.key}'. Cannot use string key '{target_key}' on a non-dict.")
                        
                        if op.operation == 'add':
                            if target_key in parent_ref:
                                raise KeyError(f"Cannot add key '{op.key}': key already exists. Use 'replace' instead.")
                            parent_ref[target_key] = op.value
                        elif op.operation == 'replace':
                            if target_key not in parent_ref:
                                raise KeyError(f"Cannot replace key '{op.key}': key does not exist. Use 'add' instead.")
                            parent_ref[target_key] = op.value
                        elif op.operation == 'delete':
                            if target_key not in parent_ref:
                                raise KeyError(f"Cannot delete key '{op.key}': key does not exist.")
                            del parent_ref[target_key]

            # Write all documents back to the file
            p_path.parent.mkdir(parents=True, exist_ok=True)
            with open(p_path, "w") as f:
                yaml.dump_all(docs, f)

            return f"✅ YAML file '{p_path}' updated successfully."

        except (KeyError, ValueError, TypeError, IndexError, Exception) as e:
            return f"Error editing YAML file: {e}"

