"""
Test script for file_edit_tool.py

This script demonstrates how to use the FileCreateTool, FileEditTool, and FileReadTool.
It follows the dependency injection pattern as specified in the project.
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
    """Main function to demonstrate file edit tools."""
    # Create a container and wire it
    container = Container()
    
    # Get the tools from the container
    create_tool = container.file_create_tool()
    edit_tool = container.file_edit_tool()
    read_tool = container.file_read_tool()
    
    # Test file path (will be created in the project root)
    test_file = "test_output/test_file.txt"
    
    # Step 1: Create a new file
    logger.info(f"Step 1: Creating file {test_file}")
    create_result = create_tool.run(file_path=test_file, content="Hello, world!\nThis is a test file.\nLine 3.")
    logger.info(f"Create result: {create_result}")
    
    # Step 2: Read the file content
    logger.info(f"\nStep 2: Reading file {test_file}")
    read_result = read_tool.run(file_path=test_file)
    logger.info(f"Read result: {read_result}")
    
    # Step 3: Edit the file using massedit expressions
    logger.info(f"\nStep 3: Editing file with expressions")
    edit_result = edit_tool.run(
        file_path=test_file,
        expressions=[
            "re.sub('Hello', 'Hi', line)",
            "re.sub('test file', 'example document', line)"
        ]
    )
    logger.info(f"Edit result: {edit_result}")
    
    # Step 4: Read the modified file
    logger.info(f"\nStep 4: Reading modified file")
    read_result = read_tool.run(file_path=test_file)
    logger.info(f"Read result: {read_result}")
    
    # Step 5: Replace the entire file content
    logger.info(f"\nStep 5: Replacing entire file content")
    edit_result = edit_tool.run(
        file_path=test_file,
        content="This is completely new content.\nThe file has been overwritten."
    )
    logger.info(f"Edit result: {edit_result}")
    
    # Step 6: Read the final file
    logger.info(f"\nStep 6: Reading final file")
    read_result = read_tool.run(file_path=test_file)
    logger.info(f"Read result: {read_result}")
    
    logger.info("\nAll tests completed successfully!")

if __name__ == "__main__":
    main()
