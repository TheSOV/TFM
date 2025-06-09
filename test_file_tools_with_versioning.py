"""
Test file for the FileCreateTool and FileEditTool with versioning integration.

This test verifies that:
1. Files can be created with proper versioning
2. Files can be edited with proper versioning
3. Version history is correctly maintained
"""

import os
import unittest
from pathlib import Path
import shutil
import uuid
import logging

from src.crewai.tools.file_edit_tool import FileCreateTool, FileEditTool, FileReadTool
from src.version_control.versioning_utils import FileVersioning
from src.services_registry.services import get, init_services

from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)


class SimpleFileVersioningTest(unittest.TestCase):
    """Simple tests for file operations with versioning.
    
    This test case verifies that the file creation and editing tools properly integrate with
    the versioning system by creating and modifying files and checking that they are properly
    committed to version control with appropriate history tracking.
    """

    def setUp(self) -> None:
        """Initialize services from the services registry.
        
        This method initializes all services and gets references to the
        file creation, editing, and versioning tools for testing.
        
        Returns:
            None
        """
        init_services()
        self.create_tool = get("file_create")
        self.edit_tool = get("file_edit")
        self.read_tool = get("file_read")
        self.versioning = get("file_versioning")
    
    def test_create_file_with_versioning(self) -> None:
        """Test creating a file and verify versioning.
        
        This test creates a file with unique name, verifies it was created successfully,
        and checks that it was properly committed to version control with the correct
        commit message.
        
        Returns:
            None
        """
        # Generate a unique file name
        file_name = f"test_file_{uuid.uuid4().hex[:8]}.txt"
        content = "This is a test file.\nCreated for versioning test.\nEnd of file."
        comment = "Test file creation with versioning"
        
        # Create the file using the tool from services registry
        result = self.create_tool._run(file_path=file_name, content=content, comment=comment)
        
        try:
            # Verify the file was created successfully
            self.assertTrue(result["success"], "File creation failed")
            
            # Verify versioning metadata was returned
            self.assertTrue(result.get("versioned", False), "File was not versioned")
            self.assertIsNotNone(result.get("commit_sha"), "No commit SHA returned")
            
            # Get file history and verify commit
            history = self.versioning.get_file_history(file_name)
            self.assertEqual(len(history), 1, "Expected exactly one commit in history")
            self.assertEqual(history[0]["message"], comment, "Commit message doesn't match")
            
            print(f"File created and versioned successfully: {file_name}")
            print(f"Commit SHA: {result.get('commit_sha')}")
        finally:
            # Clean up - remove the file if it exists
            full_path = os.path.join(os.getenv("TEMP_FILES_DIR", ""), file_name)
            if os.path.exists(full_path):
                os.remove(full_path)
                print(f"Cleaned up test file: {full_path}")
                
    def test_edit_file_with_versioning(self) -> None:
        """Test editing a file and verify versioning history.
        
        This test creates a file, edits it, and verifies that both versions
        are properly tracked in version control with correct commit messages.
        
        Returns:
            None
        """
        # Generate a unique file name
        file_name = f"edit_test_{uuid.uuid4().hex[:8]}.txt"
        initial_content = "Initial content\nLine 2\nLine 3"
        create_comment = "Initial file creation for edit test"
        
        # First create the file
        print(f"Creating file for edit test: {file_name}")
        create_result = self.create_tool._run(
            file_path=file_name, 
            content=initial_content, 
            comment=create_comment
        )
        self.assertTrue(create_result["success"], "File creation failed")
        
        # Now edit the file
        edit_comment = "Updated file content"
        new_content = "Modified content\nLine 2 changed\nLine 3\nLine 4 added"
        
        print(f"Editing file: {file_name}")
        edit_result = self.edit_tool._run(
            file_path=file_name,
            content=new_content,
            comment=edit_comment
        )
        
        try:
            # Verify edit was successful
            self.assertTrue(edit_result["success"], "File edit failed")
            
            # Verify versioning information
            self.assertTrue(edit_result.get("versioned", False), "File edit was not versioned")
            self.assertIsNotNone(edit_result.get("commit_sha"), "No commit SHA returned for edit")
            
            # Verify file content was updated
            read_result = self.read_tool._run(file_path=file_name)
            self.assertEqual(read_result["content"], new_content, "File content not updated correctly")
            
            # Verify file history now has two entries
            history = self.versioning.get_file_history(file_name)
            self.assertEqual(len(history), 2, "Expected exactly two commits in history")
            
            # Most recent commit (edit) should be first
            self.assertEqual(history[0]["message"], edit_comment, "Edit commit message doesn't match")
            # Initial commit should be second
            self.assertEqual(history[1]["message"], create_comment, "Initial commit message doesn't match")
            
            print(f"File edited and versioned successfully: {file_name}")
            print(f"Edit commit SHA: {edit_result.get('commit_sha')}")
        finally:
            # Clean up - remove the file if it exists
            full_path = os.path.join(os.getenv("TEMP_FILES_DIR", ""), file_name)
            if os.path.exists(full_path):
                os.remove(full_path)
                print(f"Cleaned up test file: {full_path}")


    def test_restore_file_with_versioning(self) -> None:
        """Test restoring a file to a previous version.
        
        This test creates a file, edits it, and then restores it to the original version,
        verifying that the restore operation works correctly with the versioning system.
        
        Returns:
            None
        """
        # Generate a unique file name
        file_name = f"restore_test_{uuid.uuid4().hex[:8]}.txt"
        initial_content = "Original content\nLine 2\nLine 3"
        create_comment = "Initial file creation for restore test"
        
        # First create the file
        print(f"Creating file for restore test: {file_name}")
        create_result = self.create_tool._run(
            file_path=file_name, 
            content=initial_content, 
            comment=create_comment
        )
        self.assertTrue(create_result["success"], "File creation failed")
        initial_sha = create_result.get("commit_sha")
        
        # Now edit the file
        edit_comment = "Update file before restore test"
        new_content = "Modified content\nLine 2 changed\nLine 3 changed\nLine 4 added"
        
        print(f"Editing file before restore: {file_name}")
        edit_result = self.edit_tool._run(
            file_path=file_name,
            content=new_content,
            comment=edit_comment
        )
        self.assertTrue(edit_result["success"], "File edit failed")
        
        try:
            # Verify current content is the edited version
            read_result = self.read_tool._run(file_path=file_name)
            self.assertEqual(read_result["content"], new_content, "File content not updated correctly")
            
            # Restore to original version
            print(f"Restoring file to original version with SHA: {initial_sha}")
            self.versioning.restore_file(file_name, initial_sha)
            
            # Verify restored content matches the original
            read_result_after_restore = self.read_tool._run(file_path=file_name)
            self.assertEqual(read_result_after_restore["content"], initial_content, 
                             "File content not restored correctly")
            
            print(f"File restored successfully to original version")
        finally:
            # Clean up - remove the file if it exists
            full_path = os.path.join(os.getenv("TEMP_FILES_DIR", ""), file_name)
            if os.path.exists(full_path):
                os.remove(full_path)
                print(f"Cleaned up test file: {full_path}")


if __name__ == "__main__":
    unittest.main()
