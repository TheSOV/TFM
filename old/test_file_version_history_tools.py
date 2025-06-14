"""
Tests for the file version history tools.

This module contains tests for the FileVersionHistoryTool, FileVersionDiffTool,
and FileVersionRestoreTool classes, which provide user-friendly access to version
control features using indices instead of commit SHAs.
"""

import os
import unittest
import uuid
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Import services registry
from src.services_registry.services import init_services, get

# Configure logging with stream handler to ensure logs are printed to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class FileVersionHistoryToolsTest(unittest.TestCase):
    """
    Test case for the file version history tools.
    
    Tests the functionality of the FileVersionHistoryTool, FileVersionDiffTool,
    and FileVersionRestoreTool classes, which provide user-friendly access to
    version control features.
    """
    
    @classmethod
    def setUpClass(cls) -> None:
        """
        Set up the test environment.
        
        Initializes services and gets the required tools from the registry.
        """
        # Load environment variables
        load_dotenv()
        
        # Initialize services
        init_services()
        
        # Get the tools from the registry
        cls.create_tool = get("file_create")
        cls.edit_tool = get("file_edit")
        cls.read_tool = get("file_read")
        cls.history_tool = get("file_version_history")
        cls.diff_tool = get("file_version_diff")
        cls.restore_tool = get("file_version_restore")
        cls.versioning = get("file_versioning")
        
        # Log the test environment
        logger.info(f"Test environment set up with temp directory: {os.getenv('TEMP_FILES_DIR', '')}")
    
    def test_version_history_workflow(self) -> None:
        """
        Test the complete version history workflow.
        
        This test creates a file, edits it multiple times, views the version history,
        gets diffs between versions, and restores to a previous version.
        
        Returns:
            None
        """
        # Generate a unique file name
        file_name = f"version_history_test_{uuid.uuid4().hex[:8]}.txt"
        logger.info(f"Testing version history workflow with file: {file_name}")
        
        # Create initial file
        initial_content = "Version 1 content\nLine 2\nLine 3"
        create_comment = "Initial file creation"
        
        create_result = self.create_tool._run(
            file_path=file_name,
            content=initial_content,
            comment=create_comment
        )
        self.assertTrue(create_result["success"], "File creation failed")
        self.assertTrue(create_result.get("versioned", False), "File creation was not versioned")
        
        # First edit
        edit1_content = "Version 2 content\nLine 2 modified\nLine 3\nLine 4 added"
        edit1_comment = "First edit - add line and modify content"
        
        edit1_result = self.edit_tool._run(
            file_path=file_name,
            content=edit1_content,
            comment=edit1_comment
        )
        self.assertTrue(edit1_result["success"], "First edit failed")
        self.assertTrue(edit1_result.get("versioned", False), "First edit was not versioned")
        
        # Second edit
        edit2_content = "Version 3 content\nLine 2 modified again\nLine 3 changed\nLine 4 modified\nLine 5 added"
        edit2_comment = "Second edit - more modifications"
        
        edit2_result = self.edit_tool._run(
            file_path=file_name,
            content=edit2_content,
            comment=edit2_comment
        )
        self.assertTrue(edit2_result["success"], "Second edit failed")
        self.assertTrue(edit2_result.get("versioned", False), "Second edit was not versioned")
        
        try:
            # Get version history
            history_result = self.history_tool._run(file_path=file_name)
            self.assertTrue(history_result["success"], "Failed to get version history")
            
            # Verify history has 3 versions (create + 2 edits)
            versions = history_result.get("versions", [])
            self.assertEqual(len(versions), 3, f"Expected 3 versions, got {len(versions)}")
            
            # Verify version indices
            self.assertEqual(versions[0]["index"], 0, "Most recent version should have index 0")
            self.assertEqual(versions[1]["index"], 1, "Second version should have index 1")
            self.assertEqual(versions[2]["index"], 2, "First version should have index 2")
            
            # Verify commit messages
            self.assertEqual(versions[2]["message"], create_comment, "Initial commit message mismatch")
            self.assertEqual(versions[1]["message"], edit1_comment, "First edit commit message mismatch")
            self.assertEqual(versions[0]["message"], edit2_comment, "Second edit commit message mismatch")
            
            # Get diff between versions 1 and 0 (first edit and second edit)
            diff_result = self.diff_tool._run(
                file_path=file_name,
                old_version_index=1,
                new_version_index=0
            )
            self.assertTrue(diff_result["success"], "Failed to get version diff")
            self.assertIn("diff", diff_result, "Diff result missing diff content")
            
            # Verify the current content is from the latest edit
            read_result = self.read_tool._run(file_path=file_name)
            self.assertEqual(read_result["content"], edit2_content, "Current content doesn't match latest edit")
            
            # Restore to the first version (index 2)
            restore_result = self.restore_tool._run(
                file_path=file_name,
                version_index=2
            )
            self.assertTrue(restore_result["success"], "Failed to restore version")
            
            # Verify the content is now the initial content
            read_after_restore = self.read_tool._run(file_path=file_name)
            self.assertEqual(read_after_restore["content"], initial_content, 
                             "Content after restore doesn't match initial content")
            
            # Verify the restore result contains the expected fields
            self.assertIn("file_path", restore_result, "Restore result should contain file_path")
            self.assertIn("restored_version", restore_result, "Restore result should contain restored_version")
            self.assertIn("restore_commit_sha", restore_result, "Restore result should contain restore_commit_sha")
            self.assertIn("message", restore_result, "Restore result should contain message")
            
            # Get updated history after restore
            updated_history = self.history_tool._run(file_path=file_name)
            self.assertTrue(updated_history["success"], "Failed to get updated history")
            
            # Verify history now has 4 versions (create + 2 edits + restore)
            updated_versions = updated_history.get("versions", [])
            self.assertEqual(len(updated_versions), 4, f"Expected 4 versions after restore, got {len(updated_versions)}")
            
            # Verify the latest commit is the restore commit
            self.assertIn("Restored", updated_versions[0]["message"], 
                          "Latest commit should be the restore commit")
            
            logger.info("Version history workflow test completed successfully")
            
        finally:
            # Clean up - remove the file if it exists
            full_path = os.path.join(os.getenv("TEMP_FILES_DIR", ""), file_name)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Cleaned up test file: {full_path}")


if __name__ == "__main__":
    unittest.main()
