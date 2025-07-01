"""
File Editing Tool using massedit

A set of tools for creating, editing, and reading files freely without structural constraints.
Uses massedit library for file manipulation. Provides simple operations to:
1. Create new files
2. Edit existing files
3. Read file content
"""
import logging
import os
import difflib
from typing import List, Optional, Dict, Any, Type, Union, Literal
from pathlib import Path
from textwrap import dedent

from pydantic import BaseModel, Field, PrivateAttr, field_validator, ValidationInfo
from crewai.tools import BaseTool

import massedit  # Library for mass editing text files

_logger = logging.getLogger(__name__)

class FileCreateRequest(BaseModel):
    """
    Request model for creating a new file.
    
    Attributes:
        file_path (str): Path to the file to create, relative to base directory.
                       Use forward slashes ('/') for cross-platform compatibility.
        content (str): Content to write to the new file. For multi-line content,
                     use '\n' for line breaks and ensure proper escaping in JSON.
        comment (str): Optional comment for version control commit message.
                      If not provided, a default message will be used.
    """
    file_path: str = Field(
        ...,
        description=("Path to the file to create, relative to base directory. "
                   "Use forward slashes ('/') for cross-platform compatibility.")
    )
    content: str = Field(
        ...,
        description=("Content to write to the new file. For multi-line content, "
                   "use '\\n' for line breaks. Ensure proper escaping in JSON.")
    )
    comment: str = Field(
        ...,
        description=("Comment for version control commit message. "
                   "Describes the purpose of this file creation. This field is mandatory.")
    )


class LineOperation(BaseModel):
    """
    Model for a line-specific operation in a file.
    
    Attributes:
        line_number (int): The line number to operate on (1-based indexing).
        operation (str): The type of operation ('add', 'replace', or 'delete').
        content (Optional[str]): The content for 'add' or 'replace' operations.
            - Required for 'add' and 'replace' operations.
            - Must not be empty for 'add' operations.
            - Must be None for 'delete' operations.
    """
    line_number: int = Field(..., description="Line number to modify (1-based indexing)")
    operation: Literal["add", "replace", "delete"] = Field(..., description="Operation type: 'add', 'replace', or 'delete'")
    content: Optional[str] = Field(
        None,
        description=(
            "Content for 'add' or 'replace' operations. "
            "Required and must not be empty for 'add' operations. "
            "Required for 'replace' operations. "
            "Must be None for 'delete' operations."
        )
    )
    
    @field_validator('content')
    def validate_content_based_on_operation(cls, v: Optional[str], info: 'ValidationInfo'):
        if 'operation' in info.data:
            operation = info.data['operation']
            if operation in ['add', 'replace']:
                if v is None:
                    raise ValueError(f"Content is required for '{operation}' operation")
                if operation == 'add' and not v.strip():
                    raise ValueError("Content cannot be empty for 'add' operation")
            elif operation == 'delete' and v is not None:
                raise ValueError("Content must be None for 'delete' operation")
        return v


class FileEditRequest(BaseModel):
    """
    Request model for editing an existing file.
    
    Attributes:
        file_path (str): Path to the file to edit, relative to base directory.
        expressions (Optional[List[str]]): List of Python expressions to modify the file content.
            Each expression must reference the 'line' variable.
        line_operations (Optional[List[LineOperation]]): Line-specific operations.
            Takes precedence over expressions.
        comment (str): Comment for version control commit message.
            This field is mandatory.
    """
    file_path: str = Field(..., description="Path to the file to edit, relative to base directory")
    expressions: Optional[List[str]] = Field(None, 
        description="List of Python expressions to modify each line. Use 'line' variable to reference current line.")
    line_operations: Optional[List[LineOperation]] = Field(None,
        description="List of line-specific operations to perform on the file")
    comment: str = Field(
        ...,
        description="Comment for version control commit message. Describes the purpose of this edit. This field is mandatory."
    )


class FileReadRequest(BaseModel):
    """
    Request model for reading a file.
    
    Attributes:
        file_path (str): Path to the file to read, relative to base directory.
        start_line (Optional[int]): Optional line number to start reading from (inclusive).
        end_line (Optional[int]): Optional line number to stop reading at (inclusive).
    """
    file_path: str = Field(..., description="Path to the file to read, relative to base directory")
    start_line: Optional[int] = Field(None, description="Optional line number to start reading from (inclusive). Defaults to the beginning of the file.")
    end_line: Optional[int] = Field(None, description="Optional line number to stop reading at (inclusive). Defaults to the end of the file.")


class FileCreateTool(BaseTool):
    """
    Tool for creating a new file with given content.
    
    Parameters:
        base_dir (str | Path): The base directory for all file operations.
        versioning (Optional): FileVersioning instance for version control.
    """
    name: str = "file_create"
    description: str = (
        "Creates a new file with your specified content. If the file already exists, this tool will not work. Never add temp at the beginning of the file path. Directly use the file path."
        "\n\nHOW TO USE THIS TOOL:\n"
        "- Provide a single JSON object (dictionary) with keys: 'file_path', 'content', and optionally 'comment'.\n"
        "- DO NOT provide a list/array or combine multiple operations in one call—this will result in an error.\n"
        "- Only one file creation operation is allowed per call.\n"
        "- 'file_path' should be a string using forward slashes ('/'), e.g., 'folder/my_file.txt'.\n"
        "- 'content' should be a string. For multi-line content, use '\\n' for line breaks.\n"
        "- 'comment' is optional and will be used as the version control commit message.\n"
        "- When using JSON, escape special characters properly:\n"
        "  - Double quotes: \\\"\n"
        "  - Newlines: \\n\n"
        "  - Backslashes: \\\\\n"
        "- IMPORTANT: Do NOT add backslashes at the end of each line in your content. This will cause issues with YAML files.\n\n"
        "\nEXAMPLES:\n"
        "1. Create a simple text file:\n"
        "   {\"file_path\": \"notes/reminder.txt\", \"content\": \"Remember to call John tomorrow.\", \"comment\": \"Add reminder note\"}\n"
        "2. Create a Python script with multiple lines:\n"
        "   {\"file_path\": \"scripts/hello.py\", \"content\": \"def hello():\\n    print('Hello, world!')\\n\\nif __name__ == '__main__':\\n    hello()\", \"comment\": \"Add hello world script\"}\n"
        "3. Create a YAML configuration file:\n"
        "   {\"file_path\": \"config/settings.yaml\", \"content\": \"# YAML example - note NO backslashes at end of lines\\ndatabase:\\n  host: localhost\\n  port: 5432\\n  name: myapp\\n\\nserver:\\n  port: 3000\\n  environment: production\", \"comment\": \"Add application configuration\"}\n"
        "4. Create a JSON file (note escaped quotes):\n"
        "   {\"file_path\": \"data/config.json\", \"content\": \"{\\\"api_key\\\": \\\"your-api-key\\\", \\\"timeout\\\": 30, \\\"enabled\\\": true}\", \"comment\": \"Add API configuration\"}\n"
        "\nTROUBLESHOOTING:\n"
        "- If you see 'not a valid key, value dictionary' errors, you are likely passing an array (list) or combining multiple operations.\n"
        "  INVALID (will fail):\n    [\n      {\"file_path\": \"file1.txt\", \"content\": \"foo\"},\n      {\"file_path\": \"file2.txt\", \"content\": \"bar\"}\n    ]\n"
        "  VALID (will succeed):\n    {\"file_path\": \"file1.txt\", \"content\": \"foo\", \"comment\": \"Add foo file\"}\n"
        "  Only a single dictionary/object is allowed per call.\n"
        "- If you see extra backslashes, ensure you're not double-escaping the content.\n"
        "- For multi-line content, use '\\n' for line breaks, not actual newlines.\n"
        "- When in doubt, test your JSON in a validator to ensure proper escaping."
    )
    args_schema: Type[BaseModel] = FileCreateRequest
    _base_dir: str = PrivateAttr()
    
    def __init__(
        self, 
        base_dir: Union[str, Path], 
        versioning: None, 
        enable_versioning: bool = False ,
        **kwargs) -> None:
        """
        Initialize the FileCreateTool.  
        
        Args:
            base_dir (str | Path): The base directory for all file operations.
            versioning: Optional FileVersioning instance for version control.
        """
        super().__init__(**kwargs)
        self._base_dir = Path(base_dir)
        self._enable_versioning = enable_versioning
        self._versioning = versioning if enable_versioning else None
    
    def _run(self, file_path: str, content: str, comment: str, enable_config_validator: bool = True) -> Dict[str, Any]:
        """
        Create a new file with the specified content and add it to version control.
        
        Args:
            file_path (str): Path to the file to create, relative to base_dir.
                Use forward slashes ('/') for OS-agnostic paths.
            content (str): Content to write to the new file.
            comment (str): Comment for version control commit message.
            
        Returns:
            Dict[str, Any]: Result of the operation, including success status and details.
        """
        try:
            # Standardize path handling
            relative_path = os.path.normpath(file_path).replace('\\', '/').lstrip('/')
            full_path = self._base_dir / relative_path
            _logger.info(f"Attempting to create file at resolved path: {full_path}")

            # Ensure the parent directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file already exists
            if full_path.exists():
                _logger.error(f"File creation failed: file already exists at {full_path}")
                return {
                    "success": False,
                    "error": f"File already exists: {file_path}",
                    "details": "Use the file_edit tool to modify existing files."
                }

            # Write the content to the file
            full_path.write_text(content, encoding='utf-8')
            
            # Add to version control if versioning is available
            commit_sha = None
            versioning_error_message = None
            if self._enable_versioning and self._versioning:
                try:
                    # Add the file to version control
                    self._versioning.add_file(file_path)
                    
                    # Commit the changes
                    commit_sha = self._versioning.commit_changes(comment)
                    _logger.info(f"File {file_path} added to version control with commit {commit_sha}")
                except Exception as ve:
                    _logger.error(f"Failed to version created file {file_path}: {str(ve)}")
                    versioning_error_message = f"File written to disk, but versioning failed: {str(ve)}"

            # Prepare result for file creation
            result = {
                "success": True # File creation itself was successful
            }
            
            # Add versioning status to result
            if self._enable_versioning and self._versioning:
                if commit_sha:
                    result["versioned"] = True
                else:
                    result["versioned"] = False
                    if versioning_error_message:
                        result["versioning_error"] = versioning_error_message
                    else:
                        # This case implies self._versioning was true but commit_sha is None without an exception - unlikely with current FileVersioning
                        result["versioning_error"] = "Versioning attempted but commit_sha not obtained, reason unknown."
            
            return result
            
        except Exception as e:
            _logger.error(f"Error creating file {file_path}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "details": f"Failed to create file: {file_path}"
            }


class FileEditTool(BaseTool):
    """
    Tool for editing an existing file using line operations, expressions, or complete content replacement.
    
    Parameters:
        base_dir (str | Path): The base directory for all file operations.
        versioning (Optional): FileVersioning instance for version control.
    """
    name: str = "file_edit"
    description: str = dedent("""\
        A tool for making precise, line-by-line changes to existing files. You can add, replace, or delete specific lines of code or text.

        **HOW TO USE:**
        1.  **Specify the file** you want to edit using the `file_path`.
        2.  **Provide a list of `line_operations`**, where each operation is a dictionary specifying the `line_number`, the `operation` ('add', 'replace', or 'delete'), and the `content` (for 'add' and 'replace').

        **IMPORTANT NOTES:**
        -  Use forward slashes (e.g., 'folder/file.txt') for `file_path`.
        -  For multi-line content, use `\\n` to indicate line breaks.
        -  You can perform multiple operations in a single call.

        **EXAMPLES:**

        **1. Add a new line:**
           ```json
           {
             "file_path": "src/main.py",
             "line_operations": [
               {"line_number": 10, "operation": "add", "content": "# This is a new comment"}
             ]
           }
           ```

        **2. Replace a line:**
           ```json
           {
             "file_path": "config.yaml",
             "line_operations": [
               {"line_number": 5, "operation": "replace", "content": "new_setting: true"}
             ]
           }
           ```

        **3. Delete a line:**
           ```json
           {
             "file_path": "README.md",
             "line_operations": [
               {"line_number": 2, "operation": "delete"}
             ]
           }
           ```

        **4. Multiple operations at once:**
           ```json
           {
             "file_path": "data.csv",
             "line_operations": [
               {"line_number": 1, "operation": "delete"},
               {"line_number": 3, "operation": "replace", "content": "new,data,row"},
               {"line_number": 5, "operation": "add", "content": "another,new,row"}
             ]
           }
           ```

        **ADVANCED USAGE: Pattern-Based Changes with Expressions**
        For more complex edits, you can use the `expressions` parameter to apply a Python expression to each line of the file. This is useful for replacing text that appears on multiple lines.

        **Example: Replace a word across the entire file:**
           ```json
           {
             "file_path": "documents/letter.txt",
             "expressions": ["line.replace('old_word', 'new_word')"]
           }
           ```
    """)
    args_schema: Type[BaseModel] = FileEditRequest
    _base_dir: str = PrivateAttr()
    _versioning = PrivateAttr(default=None)
    
    def __init__(
        self, 
        base_dir: Union[str, Path], 
        versioning=None,
        enable_versioning: bool = True,
        **kwargs) -> None:
        """
        Initialize the FileEditTool.
        
        Args:
            base_dir (str | Path): The base directory for all file operations.
            versioning: Optional FileVersioning instance for version control.
        """
        super().__init__(**kwargs)
        self._base_dir = Path(base_dir)
        self._enable_versioning = enable_versioning
        self._versioning = versioning if enable_versioning else None
    
    def _run(
        self, 
        file_path: str, 
        comment: str,
        expressions: Optional[List[str]] = None, 
        line_operations: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Edit an existing file using one of two methods: expressions or line operations.
        Then add the changes to version control.
        
        Args:
            file_path (str): Path to the file to edit, relative to base_dir.
                Use forward slashes ('/') for OS-agnostic paths.
            expressions (Optional[List[str]]): List of Python expressions to modify the file content.
            line_operations (Optional[List[Dict[str, Any]]]): List of line-specific operations to perform.
            comment (str): Comment for version control commit message.
            
        Returns:
            Dict[str, Any]: Result of the operation, including success status and details.
            
        Raises:
            ValueError: If no valid edit operation is provided.
        """
        try:
            # Standardize path handling
            relative_path = os.path.normpath(file_path).replace('\\', '/').lstrip('/')
            full_path = self._base_dir / relative_path
            _logger.info(f"Attempting to edit file at resolved path: {full_path}")

            # Check if file exists
            if not full_path.exists():
                _logger.error(f"File edit failed: file does not exist at {full_path}")
                return {
                    "success": False,
                    "error": f"File '{file_path}' does not exist. Use the file_create tool to create it first."
                }
            
            # Store original content for diff
            original_content = full_path.read_text(encoding="utf-8")
            original_lines = original_content.splitlines()
            

            
            # If line operations are provided, apply them directly
            if line_operations is not None and len(line_operations) > 0:
                # Convert to LineOperation objects to validate operations
                validated_ops = []
                for op in line_operations:
                    try:
                        validated_ops.append(LineOperation(**op))
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"Invalid line operation: {str(e)}",
                            "details": {"operation": op}
                        }
                
                # Sort operations by line number (descending) to avoid line number shifts
                # This ensures delete/replace happens before add when considering same line number
                validated_ops.sort(key=lambda x: (x.line_number, 0 if x.operation == "add" else -1), reverse=True)
                
                # Apply operations
                changed_lines = original_lines.copy()
                operations_applied = 0
                
                for op in validated_ops:
                    # Adjust for zero-based indexing and validate line number
                    index = op.line_number - 1
                    if op.operation == "add":
                        if 0 <= index <= len(changed_lines):
                            if not op.content:
                                return {
                                    "success": False,
                                    "error": f"Content is required for 'add' operation at line {op.line_number}",
                                    "details": {"operation": op.dict()}
                                }
                            changed_lines.insert(index + 1, op.content)  # Add after the line_number
                            operations_applied += 1
                        else:
                            return {
                                "success": False,
                                "error": f"Line number {op.line_number} out of range for 'add' operation",
                                "details": {"operation": op.dict(), "file_lines": len(original_lines)}
                            }
                    elif op.operation == "replace":
                        if 0 <= index < len(changed_lines):
                            if not op.content:
                                return {
                                    "success": False,
                                    "error": f"Content is required for 'replace' operation at line {op.line_number}",
                                    "details": {"operation": op.dict()}
                                }
                            changed_lines[index] = op.content
                            operations_applied += 1
                        else:
                            return {
                                "success": False,
                                "error": f"Line number {op.line_number} out of range for 'replace' operation",
                                "details": {"operation": op.dict(), "file_lines": len(original_lines)}
                            }
                    elif op.operation == "delete":
                        if 0 <= index < len(changed_lines):
                            changed_lines.pop(index)
                            operations_applied += 1
                        else:
                            return {
                                "success": False,
                                "error": f"Line number {op.line_number} out of range for 'delete' operation",
                                "details": {"operation": op.dict(), "file_lines": len(original_lines)}
                            }
                
                # Write the modified lines back to the file
                new_content = "\n".join(changed_lines)
                if len(changed_lines) > 0:  # Add final newline if there are lines
                    new_content += "\n"
                    
                full_path.write_text(new_content, encoding="utf-8")
                
                # Generate unified diff for line operations
                diff = list(difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile='original',
                    tofile='modified',
                    lineterm=''
                ))
                
                # Add to version control if versioning is available
                commit_sha = None
                versioning_error_message = None
                if self._enable_versioning and self._versioning:
                    try:
                        # Add the file to version control
                        self._versioning.add_file(file_path)
                        
                        # Commit the changes
                        commit_sha = self._versioning.commit_changes(comment)
                        _logger.info(f"File {file_path} edited and committed to version control with commit {commit_sha}")
                    except Exception as ve:
                        _logger.error(f"Failed to version edited file {file_path} (line_operations/expressions): {str(ve)}")
                        versioning_error_message = f"File edited, but versioning failed: {str(ve)}"
            
                # Prepare result
                result = {
                    "success": True, # File edit itself was successful
                    "message": f"File {file_path} edited successfully using provided operations/expressions.",
                    "details": {
                        "diff": "\n".join(diff) if diff else "No changes detected."
                    }
                }

                # Add versioning status to result
                if self._enable_versioning and self._versioning:
                    if commit_sha:
                        result["versioned"] = True
                        result["commit_sha"] = commit_sha
                        result["version_comment"] = comment
                        # For backward compatibility with potential consumers of details.versioned
                        result["details"]["versioned"] = True
                        result["details"]["commit_sha"] = commit_sha
                        result["details"]["version_comment"] = comment
                    else:
                        result["versioned"] = False
                        if versioning_error_message:
                            result["versioning_error"] = versioning_error_message
                        else:
                            result["versioning_error"] = "Versioning attempted but commit_sha not obtained, reason unknown."
                        result["details"]["versioned"] = False # For backward compatibility
            
                return result
            
            # If expressions are provided, use massedit to apply them (third precedence)
            elif expressions is not None and len(expressions) > 0:
                # Convert Path to string for massedit
                str_path = str(full_path)
                
                # Apply expressions to file using massedit
                massedit.edit_files([str_path], expressions=expressions, dry_run=False)
                
                # Read new content to check changes
                new_content = full_path.read_text(encoding="utf-8")
                changes = "No changes" if original_content == new_content else f"{len(expressions)} expression(s) applied"
                
                # Generate unified diff for expressions
                diff = list(difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile='original',
                    tofile='modified',
                    lineterm=''
                ))
                
                # Add to version control if versioning is available
                commit_sha = None
                versioning_error_message = None
                if self._enable_versioning and self._versioning:
                    try:
                        # Add the file to version control
                        self._versioning.add_file(file_path)
                        
                        # Commit the changes
                        commit_sha = self._versioning.commit_changes(comment)
                        _logger.info(f"File {file_path} edited with expressions and committed to version control with commit {commit_sha}")
                    except Exception as ve:
                        _logger.error(f"Failed to version edited file {file_path} (expressions): {str(ve)}")
                        versioning_error_message = f"File edited with expressions, but versioning failed: {str(ve)}"
                
                # Prepare result
                result = {
                    "success": True,
                    "message": f"File {file_path} edited successfully using expressions.",
                    "details": {
                        "changes": changes,
                        "expressions": expressions,
                        "diff": '\n'.join(diff)
                    }
                }
                
                # Add versioning status to result
                if self._enable_versioning and self._versioning:
                    if commit_sha:
                        result["versioned"] = True
                        result["commit_sha"] = commit_sha
                        result["version_comment"] = comment
                    else:
                        result["versioned"] = False
                        if versioning_error_message:
                            result["versioning_error"] = versioning_error_message
                        else:
                            result["versioning_error"] = "Versioning attempted but commit_sha not obtained, reason unknown."
                
                return result
            
            else:
                return {
                    "success": False,
                    "error": "No edit operation specified. Provide 'line_operations' or 'expressions'.",
                }
            
        except Exception as e:
            _logger.error(f"Error editing file {file_path}: {str(e)}")
            return {
                "success": False,
                "error": f"Error editing file: {str(e)}",
                "details": {"exception": str(e)}
            }


class FileReadTool(BaseTool):
    """
    Tool for reading the content of a file.
    
    Parameters:
        base_dir (str | Path): The base directory for all file operations.
    """
    name: str = "file_read"
    description: str = dedent("""
        A tool that can be used to read a file's content, optionally from a specific start line to an end line.

        **HOW TO USE:**
        1.  **Specify the file** you want to read using the `file_path`.
        2.  **Optionally specify `start_line` and `end_line`** to read only a specific range of lines. If omitted, the entire file is read.

        **EXAMPLES:**

        **1. Read the entire file:**
           ```json
           {
             "file_path": "src/main.py"
           }
           ```

        **2. Read a specific range of lines (e.g., lines 10 to 20):**
           ```json
           {
             "file_path": "src/main.py",
             "start_line": 10,
             "end_line": 20
           }
           ```
    """)
    args_schema: Type[BaseModel] = FileReadRequest
    _base_dir: Path = PrivateAttr()
    
    def __init__(self, base_dir: Union[str, Path], **kwargs) -> None:
        """
        Initialize the FileReadTool.
        
        Args:
            base_dir (str | Path): The base directory for all file operations.
        """
        super().__init__(**kwargs)
        self._base_dir = Path(base_dir)
    
    def _run(
        self, 
        file_path: str, 
        start_line: Optional[int] = None, 
        end_line: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Read the content of a file. The tool will return the content with line numbers.

        Args:
            file_path (str): Path to the file to read, relative to base_dir.
                Use forward slashes ('/') for OS-agnostic paths.

        Returns:
            Dict[str, Any]: Result of the operation, including success status, file content, and details.
        """
        try:
            # Standardize path handling
            relative_path = os.path.normpath(file_path).replace("\\", "/").lstrip("/")
            full_path = self._base_dir / relative_path
            _logger.info(f"Attempting to read file at path: {full_path}")

            # Check if file exists
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File {file_path} does not exist.",
                }

            # Read file content
            lines = full_path.read_text(encoding="utf-8").splitlines()

            # Slice lines if start_line or end_line are specified
            # Note: Line numbers are 1-based, list indices are 0-based
            start_index = (start_line - 1) if start_line else 0
            end_index = end_line if end_line else len(lines)

            if start_index < 0 or start_index >= len(lines):
                return {"success": False, "error": f"start_line {start_line} is out of bounds for file {file_path} with {len(lines)} lines."}
            if end_index > len(lines):
                _logger.warning(f"end_line {end_line} is out of bounds for file {file_path}, reading until the end of the file.")
                end_index = len(lines)

            lines_to_process = lines[start_index:end_index]
            
            # Add line numbers to the selected lines
            content_with_lines = "\n".join(
                f"{i + 1 + start_index:05d}: {line}" for i, line in enumerate(lines_to_process)
            )

            return {
                "success": True,
                "content": content_with_lines,
                "details": {"number_of_lines": len(lines)},
            }

        except Exception as e:
            _logger.error(f"Error reading file {file_path}: {str(e)}")
            return {
                "success": False,
                "error": f"Error reading file: {str(e)}",
                "details": {"exception": str(e)},
            }
