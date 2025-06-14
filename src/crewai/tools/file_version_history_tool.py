"""
File Version History Tool

A tool for viewing version history, generating diffs, and restoring previous versions of files.
Uses the FileVersioning utility to provide user-friendly access to version control features.
"""

from typing import Dict, List, Any, Optional, Type, Union
from pathlib import Path
import os
import logging
from pydantic import BaseModel, Field

from crewai.tools import BaseTool

# Import FileVersioning utility
from src.version_control.versioning_utils import FileVersioning, VersioningError

_logger = logging.getLogger(__name__)


class FileVersionHistoryRequest(BaseModel):
    """
    Request model for viewing file version history.
    
    Attributes:
        file_path (str): Path to the file to view history for, relative to base directory.
                       Use forward slashes ('/') for cross-platform compatibility.
    """
    file_path: str = Field(
        ...,
        description=("Path to the file to view history for, relative to base directory. "
                   "Use forward slashes ('/') for cross-platform compatibility.")
    )


class FileVersionDiffRequest(BaseModel):
    """
    Request model for viewing diff between two versions of a file.
    
    Attributes:
        file_path (str): Path to the file to view diff for, relative to base directory.
        old_version_index (int): Index of the older version (0 is the most recent).
        new_version_index (int): Index of the newer version (0 is the most recent).
    """
    file_path: str = Field(
        ...,
        description="Path to the file to view diff for, relative to base directory."
    )
    old_version_index: int = Field(
        ...,
        description="Index of the older version (0 is the most recent, 1 is the previous version, etc.)"
    )
    new_version_index: int = Field(
        ...,
        description="Index of the newer version (0 is the most recent, 1 is the previous version, etc.)"
    )


class FileVersionRestoreRequest(BaseModel):
    """
    Request model for restoring a file to a previous version.
    
    Attributes:
        file_path (str): Path to the file to restore, relative to base directory.
        version_index (int): Index of the version to restore (0 is the most recent).
    """
    file_path: str = Field(
        ...,
        description="Path to the file to restore, relative to base directory."
    )
    version_index: int = Field(
        ...,
        description="Index of the version to restore (0 is the most recent, 1 is the previous version, etc.)"
    )


class FileVersionHistoryTool(BaseTool):
    """
    Tool for viewing the version history of a file.
    
    Parameters:
        base_dir (str | Path): The base directory for all file operations.
        versioning (FileVersioning): FileVersioning instance for version control.
    """
    name: str = "file_version_history"
    description: str = (
        "View the version history of a file, showing all commits that modified the file.\n\n"
        "HOW TO USE THIS TOOL:\n"
        "- Provide a JSON object with the 'file_path' key.\n"
        "- The file path should be relative to the base directory and use forward slashes ('/').\n\n"
        "EXAMPLE:\n"
        "  {\"file_path\": \"documents/report.md\"}\n\n"
        "This will return a list of all versions of the file, with each version showing:\n"
        "- Version index (0 is the most recent)\n"
        "- Commit SHA\n"
        "- Author\n"
        "- Timestamp\n"
        "- Commit message\n\n"
        "You can use the version index with the file_version_diff and file_version_restore tools."
    )
    args_schema: Type[BaseModel] = FileVersionHistoryRequest
    
    def __init__(self, base_dir: Union[str, Path], versioning: FileVersioning, **kwargs) -> None:
        """
        Initialize the FileVersionHistoryTool.
        
        Args:
            base_dir (str | Path): The base directory for all file operations.
            versioning (FileVersioning): FileVersioning instance for version control.
        """
        super().__init__(**kwargs)
        self._base_dir = str(base_dir)
        self._versioning = versioning
    
    def _run(self, file_path: str) -> Dict[str, Any]:
        """
        Get the version history of a file.
        
        Retrieves the complete commit history for a specific file, including commit SHAs,
        authors, timestamps, and commit messages. Each version is assigned an index
        (0 for most recent) to make it easier to reference in other version control operations.
        
        Args:
            file_path (str): Path to the file to view history for, relative to base_dir.
                Use forward slashes ('/') for OS-agnostic paths.
                
        Returns:
            Dict[str, Any]: Result of the operation with the following structure:
                - success (bool): Whether the operation was successful
                - file_path (str): The relative path to the file
                - version_count (int): Number of versions found
                - versions (List[Dict]): List of version entries, each containing:
                    - index (int): Version index (0 is most recent)
                    - sha (str): Commit SHA
                    - author (str): Author of the commit
                    - timestamp (int): Unix timestamp of the commit
                    - message (str): Commit message
                
        Raises:
            Exception: If there's an error retrieving the version history
        """
        try:
            # Convert path separators to OS-specific format
            file_path = file_path.replace("/", os.path.sep)
            
            # Check if file exists
            full_path = os.path.join(self._base_dir, file_path)
            if not os.path.exists(full_path):
                return {
                    "success": False,
                    "error": f"File does not exist: {file_path}",
                    "details": "The file must exist to view its version history."
                }
            
            # Get file history from versioning
            history = self._versioning.get_file_history(file_path)
            
            # Add index to each history entry for easier reference
            for i, entry in enumerate(history):
                entry['index'] = i
            
            return {
                "success": True,
                "file_path": file_path,
                "version_count": len(history),
                "versions": history
            }
            
        except Exception as e:
            _logger.error(f"Error getting version history for {file_path}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "details": f"Failed to get version history for file: {file_path}"
            }


class FileVersionDiffTool(BaseTool):
    """
    Tool for viewing the differences between two versions of a file.
    
    Parameters:
        base_dir (str | Path): The base directory for all file operations.
        versioning (FileVersioning): FileVersioning instance for version control.
    """
    name: str = "file_version_diff"
    description: str = (
        "View the differences between two versions of a file.\n\n"
        "HOW TO USE THIS TOOL:\n"
        "- Provide a JSON object with 'file_path', 'old_version_index', and 'new_version_index' keys.\n"
        "- The file path should be relative to the base directory and use forward slashes ('/').\n"
        "- Version indices are from the file_version_history tool (0 is the most recent version).\n\n"
        "EXAMPLE:\n"
        "  {\"file_path\": \"documents/report.md\", \"old_version_index\": 1, \"new_version_index\": 0}\n\n"
        "This will show the differences between version 1 (older) and version 0 (newer) of the file."
    )
    args_schema: Type[BaseModel] = FileVersionDiffRequest
    
    def __init__(self, base_dir: Union[str, Path], versioning: FileVersioning, **kwargs) -> None:
        """
        Initialize the FileVersionDiffTool.
        
        Args:
            base_dir (str | Path): The base directory for all file operations.
            versioning (FileVersioning): FileVersioning instance for version control.
        """
        super().__init__(**kwargs)
        self._base_dir = str(base_dir)
        self._versioning = versioning
    
    def _run(self, file_path: str, old_version_index: int, new_version_index: int) -> Dict[str, Any]:
        """
        Get the differences between two versions of a file.
        
        Generates a unified diff showing the changes between two versions of a file
        identified by their indices in the version history. The indices make it easier
        to reference versions without needing to know the commit SHAs.
        
        Args:
            file_path (str): Path to the file to view diff for, relative to base_dir.
                Use forward slashes ('/') for OS-agnostic paths.
            old_version_index (int): Index of the older version (0 is the most recent,
                1 is the previous version, etc.)
            new_version_index (int): Index of the newer version (0 is the most recent,
                1 is the previous version, etc.)
                
        Returns:
            Dict[str, Any]: Result of the operation with the following structure:
                - success (bool): Whether the operation was successful
                - file_path (str): The relative path to the file
                - old_version (Dict): Information about the older version:
                    - index (int): Version index
                    - sha (str): Commit SHA
                    - message (str): Commit message
                - new_version (Dict): Information about the newer version:
                    - index (int): Version index
                    - sha (str): Commit SHA
                    - message (str): Commit message
                - diff (str): Unified diff showing the changes between versions
                
        Raises:
            Exception: If there's an error generating the diff or if the specified
                version indices are invalid
        """
        try:
            # Convert path separators to OS-specific format
            file_path = file_path.replace("/", os.path.sep)
            
            # Check if file exists
            full_path = os.path.join(self._base_dir, file_path)
            if not os.path.exists(full_path):
                return {
                    "success": False,
                    "error": f"File does not exist: {file_path}",
                    "details": "The file must exist to view its version differences."
                }
            
            # Get file history from versioning
            history = self._versioning.get_file_history(file_path)
            
            # Validate indices
            if old_version_index < 0 or old_version_index >= len(history):
                return {
                    "success": False,
                    "error": f"Invalid old version index: {old_version_index}",
                    "details": f"Version index must be between 0 and {len(history) - 1}."
                }
                
            if new_version_index < 0 or new_version_index >= len(history):
                return {
                    "success": False,
                    "error": f"Invalid new version index: {new_version_index}",
                    "details": f"Version index must be between 0 and {len(history) - 1}."
                }
                
            # Get the commit SHAs for the specified indices
            old_sha = history[old_version_index]['sha']
            new_sha = history[new_version_index]['sha']
            
            # Get diff between the two versions
            diff = self._versioning.get_file_diff(file_path, old_sha, new_sha)
            
            return {
                "success": True,
                "file_path": file_path,
                "old_version": {
                    "index": old_version_index,
                    "sha": old_sha,
                    "message": history[old_version_index]['message']
                },
                "new_version": {
                    "index": new_version_index,
                    "sha": new_sha,
                    "message": history[new_version_index]['message']
                },
                "diff": diff
            }
            
        except Exception as e:
            _logger.error(f"Error getting version diff for {file_path}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "details": f"Failed to get version diff for file: {file_path}"
            }


class FileVersionRestoreTool(BaseTool):
    """
    Tool for restoring a file to a previous version.
    
    Parameters:
        base_dir (str | Path): The base directory for all file operations.
        versioning (FileVersioning): FileVersioning instance for version control.
    """
    name: str = "file_version_restore"
    description: str = (
        "Restore a file to a previous version.\n\n"
        "HOW TO USE THIS TOOL:\n"
        "- Provide a JSON object with 'file_path' and 'version_index' keys.\n"
        "- The file path should be relative to the base directory and use forward slashes ('/').\n"
        "- Version index is from the file_version_history tool (0 is the most recent version).\n\n"
        "EXAMPLE:\n"
        "  {\"file_path\": \"documents/report.md\", \"version_index\": 2}\n\n"
        "This will restore the file to version 2 (the third most recent version)."
    )
    args_schema: Type[BaseModel] = FileVersionRestoreRequest
    
    def __init__(self, base_dir: Union[str, Path], versioning: FileVersioning, **kwargs) -> None:
        """
        Initialize the FileVersionRestoreTool.
        
        Args:
            base_dir (str | Path): The base directory for all file operations.
            versioning (FileVersioning): FileVersioning instance for version control.
        """
        super().__init__(**kwargs)
        self._base_dir = str(base_dir)
        self._versioning = versioning
    
    def _run(self, file_path: str, version_index: int) -> Dict[str, Any]:
        """
        Restore a file to a previous version.
        
        Restores a file to a specific version identified by its index in the version history.
        The restoration itself is recorded as a new commit in the version history, preserving
        the complete history of changes including the restoration action.
        
        Args:
            file_path (str): Path to the file to restore, relative to base_dir.
                Use forward slashes ('/') for OS-agnostic paths.
            version_index (int): Index of the version to restore (0 is the most recent,
                1 is the previous version, etc.)
                
        Returns:
            Dict[str, Any]: Result of the operation with the following structure:
                - success (bool): Whether the operation was successful
                - file_path (str): The relative path to the file
                - restored_version (Dict): Information about the restored version:
                    - index (int): Version index
                    - sha (str): Commit SHA
                    - message (str): Commit message
                - restore_commit_sha (str): SHA of the commit that performed the restoration
                - message (str): Success message describing the restoration
                
        Raises:
            Exception: If there's an error restoring the file or if the specified
                version index is invalid
        """
        try:
            # Convert path separators to OS-specific format
            file_path = file_path.replace("/", os.path.sep)
            
            # Check if file exists
            full_path = os.path.join(self._base_dir, file_path)
            if not os.path.exists(full_path):
                return {
                    "success": False,
                    "error": f"File does not exist: {file_path}",
                    "details": "The file must exist to restore a previous version."
                }
            
            # Get file history from versioning
            history = self._versioning.get_file_history(file_path)
            
            # Validate index
            if version_index < 0 or version_index >= len(history):
                return {
                    "success": False,
                    "error": f"Invalid version index: {version_index}",
                    "details": f"Version index must be between 0 and {len(history) - 1}."
                }
                
            # Get the commit SHA for the specified index
            target_sha = history[version_index]['sha']
            
            # Restore the file to the specified version
            self._versioning.restore_file(file_path, target_sha)
            
            # Commit the restoration
            commit_message = f"Restored {file_path} to version {version_index} (commit {target_sha[:7]})"
            self._versioning.add_file(file_path)
            commit_sha = self._versioning.commit_changes(commit_message)
            
            return {
                "success": True,
                "file_path": file_path,
                "restored_version": {
                    "index": version_index,
                    "sha": target_sha,
                    "message": history[version_index]['message']
                },
                "restore_commit_sha": commit_sha,
                "message": f"File {file_path} successfully restored to version {version_index}"
            }
            
        except Exception as e:
            _logger.error(f"Error restoring version for {file_path}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "details": f"Failed to restore version for file: {file_path}"
            }
