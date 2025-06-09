"""
File Versioning Utility for managing file versions using Git-like functionality.

This module provides a high-level interface to Dulwich's porcelain API for version control
operations, making it easy to track changes to files in a directory.
"""

from pathlib import Path
from typing import List, Dict, Any, Union
from dulwich import porcelain
from dulwich.repo import Repo
from dulwich.diff_tree import tree_changes
from dulwich.object_store import tree_lookup_path
import difflib

import logging
logger = logging.getLogger(__name__)


class VersioningError(Exception):
    """Custom exception for versioning operations."""
    pass


class FileVersioning:
    """
    A utility class for managing file versions in a Git-like repository.
    
    This class provides methods to initialize a repository, track changes,
    commit versions, and view history of changes.
    """
    
    def __init__(self, repo_path: Union[str, Path]):
        """
        Initialize the FileVersioning instance.
        
        Args:
            repo_path: Path to the repository (will be created if it doesn't exist)
        """
        self.repo_path = Path(repo_path).absolute()
        self.repo = None
        self._ensure_repo()
    
    def _ensure_repo(self) -> None:
        """Ensure the repository exists, create if it doesn't."""
        if not (self.repo_path / ".git").exists():
            self.repo = porcelain.init(str(self.repo_path))
        else:
            self.repo = Repo(str(self.repo_path))
    
    def add_file(self, file_path: Union[str, Path]) -> None:
        """
        Add a file to version control.

        Args:
            file_path (Union[str, Path]): Path to the file to add (relative to repo root).

        Raises:
            VersioningError: If the file cannot be added.
        """

        try:
            repo_relative_path = Path(self.repo_path.name) / file_path
            porcelain.add(self.repo_path, str(repo_relative_path))
        except Exception as e:
            raise VersioningError(f"Failed to add file {file_path}: {str(e)}")

    
    def commit_changes(self, message: str) -> str:
        """
        Commit all staged changes.
        
        Args:
            message: Commit message
            
        Returns:
            str: The commit SHA if successful
        """
        try:
            return porcelain.commit(self.repo_path, message.encode())
        except Exception as e:
            raise VersioningError(f"Failed to commit changes: {str(e)}")
    
    def get_file_history(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Get the commit history for a specific file.

        Args:
            file_path (str): Path to the file (relative to repo root)

        Returns:
            List[Dict[str, Any]]: List of dictionaries containing commit information
        """
        history = []
        try:
            # Use file_path directly, as it is already relative to the repo root
            for entry in self.repo.get_walker(paths=[file_path.encode()]):
                commit = entry.commit
                # Always use 40-character hex SHA (decode ASCII)
                sha = commit.id.decode('ascii')
                history.append({
                    'sha': sha,
                    'author': commit.author.decode(),
                    'timestamp': commit.author_time,
                    'message': commit.message.decode().strip(),
                })
            return history
        except Exception as e:
            raise VersioningError(f"Failed to get history for {file_path}: {str(e)}")

    
    def get_file_diff(self, file_path: str, old_rev: str, new_rev: str) -> str:
        """
        Get the differences between two versions of a file.

        Args:
            file_path (str): Path to the file (relative to repo root)
            old_rev (str): Old revision (can be a commit SHA or reference like 'HEAD~1')
            new_rev (str): New revision

        Returns:
            str: Unified diff output for the specified file
        """        
        try:
            # Helper function to get file content from a specific revision
            def get_file_content_from_rev(rev, file_path):
                try:
                    # Get the commit object
                    commit = self.repo[rev.encode('ascii')]
                    # Get the tree from the commit
                    tree = commit.tree
                    object_store = self.repo.object_store
                    
                    # Debug info about the tree
                    logger.debug(f"Tree entries in revision {rev}:")
                    tree_obj = self.repo[tree]
                    for entry in tree_obj.items():
                        logger.debug(f"  - {entry.path.decode('utf-8')} ({entry.mode})")
                    
                    # Try both with and without repo folder name
                    paths_to_try = [
                        str(file_path),  # Direct file path
                        str(Path(self.repo_path.name) / file_path)  # With repo folder
                    ]
                    
                    for path_to_try in paths_to_try:
                        try:
                            logger.debug(f"Trying to get content from path: {path_to_try}")
                            # Try to find the file in the tree
                            mode, blob_id = tree_lookup_path(object_store.__getitem__, 
                                                           tree, 
                                                           path_to_try.encode('utf-8'))
                            
                            # If found, get the blob content
                            blob = object_store[blob_id]
                            content = blob.data.decode('utf-8')
                            logger.debug(f"Successfully retrieved content from: {path_to_try}")
                            return content
                        except Exception as e:
                            logger.debug(f"Failed to get content from {path_to_try}: {e}")
                    
                    # If we get here, the file wasn't found with any path
                    return None
                except Exception as e:
                    logger.debug(f"Error getting file content from {rev}: {e}")
                    return None
            
            # Get content from both revisions
            old_content = get_file_content_from_rev(old_rev, file_path)
            new_content = get_file_content_from_rev(new_rev, file_path)
            
            # Debug output
            logger.debug(f"Old content exists: {old_content is not None}")
            logger.debug(f"New content exists: {new_content is not None}")
            
            # Handle cases where content couldn't be retrieved
            if old_content is None and new_content is None:
                return f"File {file_path} not found in either revision"
            elif old_content is None:
                return f"File {file_path} only exists in {new_rev} (new)"
            elif new_content is None:
                return f"File {file_path} only exists in {old_rev} (old)"
            
            # If content is the same, no diff
            if old_content == new_content:
                return f"No changes found for {file_path} between these revisions"
            
            # Generate unified diff
            old_lines = old_content.splitlines()
            new_lines = new_content.splitlines()
            
            diff = difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
                lineterm=''
            )
            
            return '\n'.join(diff)
        except Exception as e:
            raise VersioningError(f"Failed to get diff for {file_path}: {str(e)}")

    
    def get_changes(self, old_rev: str = 'HEAD~1', new_rev: str = 'HEAD') -> List[Dict[str, Any]]:
        """
        Get all changes between two revisions.
        
        Args:
            old_rev: Old revision (default: previous commit)
            new_rev: New revision (default: current HEAD)
            
        Returns:
            List of changes with type and paths
        """
        changes = []
        try:
            old_tree = self.repo[old_rev.encode()].tree
            new_tree = self.repo[new_rev.encode()].tree
            
            for change in tree_changes(self.repo.object_store, old_tree, new_tree):
                changes.append({
                    'type': change.type.decode(),
                    'old_path': change.old.path.decode() if change.old.path else None,
                    'new_path': change.new.path.decode() if change.new.path else None,
                })
            return changes
        except Exception as e:
            raise VersioningError(f"Failed to get changes: {str(e)}")
            
    def restore_file(self, file_path: Union[str, Path], target_rev: str = 'HEAD') -> None:
        """
        Restore a file to its state in a previous revision.

        Args:
            file_path (Union[str, Path]): Path to the file to restore (relative to repo root)
            target_rev (str): Revision to restore from (default: HEAD)

        Raises:
            VersioningError: If the file doesn't exist in the target revision
        """
        from pathlib import Path
        try:
            from dulwich.object_store import tree_lookup_path
            
            file_path = Path(file_path)
            # Convert SHA to bytes correctly if it's not already bytes
            try:
                if isinstance(target_rev, bytes):
                    commit = self.repo[target_rev]
                else:
                    # Handle the case where target_rev might already be bytes
                    try:
                        commit = self.repo[target_rev.encode('ascii')]
                    except AttributeError:
                        # If target_rev is already bytes but has no encode method
                        commit = self.repo[target_rev]
            except KeyError:
                # Try to resolve the revision if it's not a direct SHA
                raise VersioningError(f"Revision {target_rev} not found")
                
            tree = commit.tree
            object_store = self.repo.object_store
            
            # Debug output to show tree contents
            logger.debug(f"Tree entries in revision {target_rev}:")
            tree_obj = self.repo[tree]
            for entry in tree_obj.items():
                logger.debug(f"  - {entry.path.decode('utf-8')} ({entry.mode})")
            
            # Try both with and without repo folder name
            paths_to_try = [
                str(file_path),  # Direct file path
                str(Path(self.repo_path.name) / file_path)  # With repo folder
            ]
            
            success = False
            for path_to_try in paths_to_try:
                try:
                    logger.debug(f"Trying to restore path: {path_to_try}")
                    mode, blob_id = tree_lookup_path(object_store.__getitem__, tree, path_to_try.encode('utf-8'))
                    blob = object_store[blob_id]
                    target_path = self.repo_path / file_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(target_path, 'wb') as f:
                        f.write(blob.data)
                    self.add_file(file_path)
                    logger.debug(f"Successfully restored file from path: {path_to_try}")
                    success = True
                    break
                except Exception as e:
                    logger.debug(f"Failed to restore from path {path_to_try}: {e}")
            
            if not success:
                raise VersioningError(f"File {file_path} not found in revision {target_rev}")
        except Exception as e:
            raise VersioningError(f"Failed to restore file {file_path}: {str(e)}") from e


def track_file_changes(repo_path: Union[str, Path], file_path: Union[str, Path], message: str) -> str:
    """
    Helper function to track changes to a single file with a single commit.
    
    Args:
        repo_path: Path to the repository
        file_path: Path to the file to track (relative to repo_path)
        message: Commit message
        
    Returns:
        str: Commit SHA if successful
    """
    vc = FileVersioning(repo_path)
    vc.add_file(file_path)
    return vc.commit_changes(message)
