import logging
from typing import List, Literal, Any, Dict, Type, Optional
from pathlib import Path

from pydantic import BaseModel, Field
from crewai.tools import BaseTool

from yamlpath.common import Parsers
from yamlpath import Processor, YAMLPath
from deepdiff import DeepDiff
from io import StringIO
from pydantic import PrivateAttr

_logger = logging.getLogger(__name__)

# YAML editor
_editor = Parsers.get_yaml_editor()

# Load YAML from file
def _load_yaml(path: Path):
    if path.exists():
        _logger.debug("Loading YAML from %s", path)
        return _editor.load(path.read_text("utf-8"))
    _logger.debug("Path %s does not exist – returning empty dict", path)
    return {}

# Save YAML to file


def _save_yaml(path: Path, data):
    """
    Save YAML data to a file, using StringIO to get the YAML string.
    Ensures the parent directory exists before writing.
    """
    _logger.debug("Writing YAML to %s", path)
    stream = StringIO()
    _editor.dump(data, stream)
    path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    path.write_text(stream.getvalue(), encoding="utf-8")

# Make processor
def _make_processor(data):
    return Processor(_logger, data)


# Pydantic models
class CreateOp(BaseModel):
    """Set operation for create tool."""

    path: str = Field(..., description="YAML Path to create")
    value: Any = Field(..., description="Value to assign")


class EditOp(BaseModel):
    """Set or delete operation for edit tool."""

    op: Literal["set", "delete"] = Field(..., description="Edit action")
    path: str = Field(..., description="YAML Path to target node(s).")
    value: Any | None = Field(None, description="Value when op='set'")


class YamlCreateRequest(BaseModel):
    file_path: str
    operations: List[CreateOp]


class YamlEditRequest(BaseModel):
    file_path: str
    operations: List[EditOp]


class YamlReadRequest(BaseModel):
    file_path: str
    path: Optional[str] = Field(None, description="YAML Path; omit for full dump")



class YamlCreateTool(BaseTool):
    """
    Tool for creating a new YAML file from an empty document using set operations.
    Returns DeepDiff delta between {{}} and the new document. Fails if the file already exists.

    Parameters:
        base_dir (str | Path): The base directory to use for all file operations. All file paths will be resolved relative to this directory.
    """
    name: str = "yaml_create"
    description: str = (
        "Create a new YAML file from an empty document using set operations. "
        "Returns DeepDiff delta between {} and the new document. Fails if the file already exists. "
        "\nUsage: Provide 'file_path' (str) for the new YAML file and 'operations' (List[CreateOp]) specifying YAML paths and values to set. "
        "Each operation is a dict with 'path' (YAMLPath string) and 'value' (any type). "
        "If the file exists, the tool returns an error. Otherwise, it writes the new YAML and returns a DeepDiff delta."
    )
    args_schema: Type[BaseModel] = YamlCreateRequest
    _base_dir: Path = PrivateAttr()

    def __init__(self, base_dir: str | Path, **kwargs) -> None:
        """
        Initialize the YamlCreateTool.

        Args:
            base_dir (str | Path): The base directory for all file operations.
        """
        super().__init__(**kwargs)
        self._base_dir = Path(base_dir)

    def _run(self, file_path: str, operations: List[Dict[str, Any]]) -> dict:
        """
        Create a new YAML file in the base directory using the provided operations.

        Args:
            file_path (str): Relative path to the YAML file (relative to base_dir).
            operations (List[Dict[str, Any]]): List of operations to perform.
        Returns:
            dict: DeepDiff delta between {{}} and the new document, or error message.
        """
        p = self._base_dir / file_path
        if p.exists():
            return "Error: File already exists"

        data: Dict[str, Any] = {}
        proc = _make_processor(data)

        for op_dict in operations:
            op = CreateOp.model_validate(op_dict)
            proc.set_value(YAMLPath(op.path), op.value)

        _save_yaml(p, data)
        diff = DeepDiff({}, data, view="tree").to_dict()
        return {"diff": diff}

# Edit tool
class YamlEditTool(BaseTool):
    """
    Tool for editing an existing YAML file with set/delete operations and returning a DeepDiff delta of changes.
    Fails if the file does not exist.

    Parameters:
        base_dir (str | Path): The base directory used for all file operations. All file paths will be resolved relative to this directory.
    """
    _base_dir: Path = PrivateAttr()

    name: str = "yaml_edit"
    description: str = (
        "Edit an existing YAML file with set/delete operations and return a DeepDiff delta of changes. Fails if the file does not exist. "
        "\nUsage: Provide 'file_path' (str) for the YAML file to edit and 'operations' (List[EditOp]) specifying edit actions. "
        "Each operation is a dict with 'op' ('set' or 'delete'), 'path' (YAMLPath string), and optionally 'value' (for 'set'). "
        "The tool applies each operation to the YAML file, saves the result, and returns a DeepDiff delta of changes. "
        "Returns an error if the file does not exist."
    )
    args_schema: Type[BaseModel] = YamlEditRequest

    def __init__(self, base_dir: str | Path, **kwargs) -> None:
        """
        Initialize the YamlEditTool.

        Args:
            base_dir (str | Path): The base directory for all file operations.
        """
        super().__init__(**kwargs)
        self._base_dir = Path(base_dir)

    def _run(self, file_path: str, operations: List[Dict[str, Any]]) -> dict:
        """
        Edit an existing YAML file in the base directory using the provided operations.

        Args:
            file_path (str): Relative path to the YAML file (relative to base_dir).
            operations (List[Dict[str, Any]]): List of edit operations to perform.
        Returns:
            dict: DeepDiff delta of changes, or error message.
        """
        p = self._base_dir / file_path
        if not p.exists():
            return "Error: File not found"

        data = _load_yaml(p)
        stream = StringIO()
        _editor.dump(data, stream)
        original = _editor.load(stream.getvalue())  # deep copy via dump/load
        proc = _make_processor(data)

        for op_dict in operations:
            op = EditOp.model_validate(op_dict)
            ypath = YAMLPath(op.path)
            if op.op == "set":
                proc.set_value(ypath, op.value)
            else:  # delete
                proc.delete_nodes(ypath)

        _save_yaml(p, data)
        diff = DeepDiff(original, data, view="tree").to_dict()
        return {"diff": diff}


# Read tool
class YamlReadTool(BaseTool):
    """
    Tool for reading YAML content. With a path, returns node values; without, returns the whole document as a string. Never modifies the file.

    Parameters:
        base_dir (str | Path): The base directory used for all file operations. All file paths will be resolved relative to this directory.
    """
    name: str = "yaml_read"
    description: str = (
        "Read YAML content. With a path, returns node values; without, returns the whole document as a string. Never modifies the file. "
        "\nUsage: Provide 'file_path' (str) for the YAML file to read. Optionally provide 'path' (YAMLPath string) to extract a specific node or value. "
        "If 'path' is omitted, the entire YAML document is returned as a string. If 'path' is provided, returns a list of matching node values. "
        "Returns an error if the file does not exist."
    )
    args_schema: Type[BaseModel] = YamlReadRequest
    _base_dir: Path = PrivateAttr()

    def __init__(self, base_dir: str | Path, **kwargs) -> None:
        """
        Initialize the YamlReadTool.

        Args:
            base_dir (str | Path): The base directory for all file operations.
        """
        super().__init__(**kwargs)
        self._base_dir = Path(base_dir)

    def _run(self, file_path: str, path: str | None = None) -> str | list | str:
        """
        Read YAML content from a file in the base directory.

        Args:
            file_path (str): Relative path to the YAML file (relative to base_dir).
            path (str | None): YAMLPath string to extract a specific node or value.
        Returns:
            str | list | str: YAML content as a string, or node values as a list, or error message.
        """
        p = self._base_dir / file_path
        if not p.exists():
            return "Error: File not found"

        data = _load_yaml(p)
        if path is None:
            stream = StringIO()
            _editor.dump(data, stream)
            return stream.getvalue()
        else:
            proc = _make_processor(data)
            ypath = YAMLPath(path)
            return [node.node for node in proc.get_nodes(ypath)]

# if __name__ == "__main__":
#     create = YamlCreateTool()
#     edit   = YamlEditTool()
#     read   = YamlReadTool()

#     current_dir = Path(__file__).parent
#     file_path = Path.joinpath(current_dir, "config.yaml")
    
#     result = create._run(
#         file_path=file_path,
#         operations=[
#             {"path": "apiVersion", "value": "v1"},
#             {"path": "data.log_level", "value": "info"}
#         ]
#     )
#     print(result)

#     result = edit._run(
#         file_path=file_path,
#         operations=[
#             {"op": "set", "path": "data.log_level", "value": "debug"},
#             {"op": "delete", "path": "metadata.deprecated"}
#         ]
#     )
#     print(result)

#     result = read._run(file_path=file_path)
#     print(result)

#     result = read._run(file_path=file_path, path="data.log_level")
#     print(result)
