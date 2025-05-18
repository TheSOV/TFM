"""
Test script for file_edit_tool.py's line operations functionality

This script demonstrates how to use the FileEditTool with line operations
for easier and more precise file editing by line number.
"""
import os
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the Python path if needed
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the necessary modules
from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Singleton, Factory
from src.crewai.tools.file_edit_tool import FileCreateTool, FileEditTool, FileReadTool

# Define a Container class for dependency injection
class Container(DeclarativeContainer):
    """Container for dependency injection."""
    
    # Configure wiring
    wiring_config = WiringConfiguration(packages=["src.crewai.tools"])
    
    # Define the base directory for file operations
    base_dir = Singleton(lambda: os.path.dirname(os.path.abspath(__file__)))
    
    # Register the file edit tools as singletons
    file_create_tool = Singleton(FileCreateTool, base_dir=base_dir)
    file_edit_tool = Singleton(FileEditTool, base_dir=base_dir)
    file_read_tool = Singleton(FileReadTool, base_dir=base_dir)

def main():
    """Main function to demonstrate file edit tools with line operations."""
    # Create a container and wire it
    container = Container()
    
    # Get the tools from the container
    create_tool = container.file_create_tool()
    edit_tool = container.file_edit_tool()
    read_tool = container.file_read_tool()
    
    # Test file path (will be created in the project root)
    test_file = "test_output/line_operations_test.txt"
    
    # Step 1: Create a new file with numbered lines for testing
    logger.info(f"Step 1: Creating file {test_file} with numbered lines")
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7\nLine 8\nLine 9\nLine 10\n"
    create_result = create_tool.run(file_path=test_file, content=content)
    logger.info(f"Create result: {create_result}")
    
    # Step 2: Read the initial file content
    logger.info(f"\nStep 2: Reading initial file content")
    read_result = read_tool.run(file_path=test_file)
    logger.info(f"Initial content:\n{read_result.get('content', '')}")
    
    # Step 3: Add a line after line 3
    logger.info(f"\nStep 3: Adding a line after line 3")
    edit_result = edit_tool.run(
        file_path=test_file,
        line_operations=[{
            "line_number": 3, 
            "operation": "add", 
            "content": "NEW LINE AFTER LINE 3"
        }]
    )
    logger.info(f"Edit result: {edit_result}")
    
    # Step 4: Read the modified file
    logger.info(f"\nStep 4: Reading file after adding a line")
    read_result = read_tool.run(file_path=test_file)
    logger.info(f"Updated content:\n{read_result.get('content', '')}")
    
    # Step 5: Replace line 5
    logger.info(f"\nStep 5: Replacing line 5")
    edit_result = edit_tool.run(
        file_path=test_file,
        line_operations=[{
            "line_number": 5, 
            "operation": "replace", 
            "content": "REPLACED LINE 5"
        }]
    )
    logger.info(f"Edit result: {edit_result}")
    
    # Step 6: Delete line 7
    logger.info(f"\nStep 6: Deleting line 7")
    edit_result = edit_tool.run(
        file_path=test_file,
        line_operations=[{
            "line_number": 7, 
            "operation": "delete"
        }]
    )
    logger.info(f"Edit result: {edit_result}")
    
    # Step 7: Multiple operations at once
    logger.info(f"\nStep 7: Performing multiple line operations at once")
    edit_result = edit_tool.run(
        file_path=test_file,
        line_operations=[
            {"line_number": 2, "operation": "add", "content": "ADDED AFTER LINE 2"},
            {"line_number": 9, "operation": "replace", "content": "REPLACED LINE 9"},
            {"line_number": 4, "operation": "delete"}
        ]
    )
    logger.info(f"Edit result: {edit_result}")
    
    # Step 8: Read the final file
    logger.info(f"\nStep 8: Reading final file content")
    read_result = read_tool.run(file_path=test_file)
    logger.info(f"Final content:\n{read_result.get('content', '')}")
    
    logger.info("\nAll line operation tests completed successfully!")

if __name__ == "__main__":
    main()
