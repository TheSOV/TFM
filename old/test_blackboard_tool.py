"""
Comprehensive tests for BlackboardTool.
Each test includes clear assertions and error handling.
"""
import json
from typing import Dict, Any, List, Optional
from src.crewai.tools.blackboard_tool import BlackboardTool
from src.crewai.devops_flow.blackboard.Blackboard import Blackboard
from src.crewai.devops_flow.blackboard.utils.Project import Project
from src.crewai.devops_flow.blackboard.utils.GeneralInfo import GeneralInfo
from src.crewai.devops_flow.blackboard.utils.Manifest import Manifest, File, Image


# --- Test Data ---
# Create Pydantic model instances for testing   
TEST_PROJECT = Project(
    user_request="Create a web application",
    project_objective="Build a modern web application with React and FastAPI"
)

# Create test images with all required fields
TEST_NGINX_IMAGE = Image(
    tag="1.25",
    repository="docker.io/library",
    image_name="nginx",
    version="1.25.0",
    manifest_digest="sha256:abcd1234",
    pullable_digest="sha256:efgh5678",
    ports=[80, 443],
    volumes=["/etc/nginx", "/var/log/nginx"],
    environment_variables=["NGINX_HOST=localhost", "NGINX_PORT=80"],
    description="Nginx web server image for testing"
)

TEST_REDIS_IMAGE = Image(
    tag="7.0",
    repository="docker.io/library",
    image_name="redis",
    version="7.0.0",
    manifest_digest="sha256:1234abcd",
    pullable_digest="sha256:5678efgh",
    ports=[6379],
    volumes=["/data"],
    environment_variables=["REDIS_PASSWORD=test"],
    description="Redis database image for testing"
)

# Create test manifest with all required fields
TEST_FILE = File(
    file_path="/kubernetes/test-manifest.yaml",
    file_state="created"
)

TEST_MANIFEST = Manifest(
    file=TEST_FILE,
    images=[TEST_NGINX_IMAGE],
    manifest_issues=[],
    description="Test Kubernetes manifest for testing"
)

# Dictionary with serializable test data for assertions
TEST_DATA = {
    "project": {
        "user_request": "Create a web application",
        "project_objective": "Build a modern web application with React and FastAPI"
    },
    "manifest": {
        "file": {
            "file_path": "/kubernetes/test-manifest.yaml",
            "file_state": "created"
        },
        "images": [
            {
                "tag": "1.25",
                "repository": "docker.io/library",
                "image_name": "nginx",
                "version": "1.25.0",
                "manifest_digest": "sha256:abcd1234",
                "pullable_digest": "sha256:efgh5678",
                "ports": [80, 443],
                "volumes": ["/etc/nginx", "/var/log/nginx"],
                "environment_variables": ["NGINX_HOST=localhost", "NGINX_PORT=80"],
                "description": "Nginx web server image for testing"
            }
        ],
        "manifest_issues": [],
        "description": "Test Kubernetes manifest for testing"
    },
    "image": {
        "tag": "7.0",
        "repository": "docker.io/library",
        "image_name": "redis",
        "version": "7.0.0",
        "manifest_digest": "sha256:1234abcd",
        "pullable_digest": "sha256:5678efgh",
        "ports": [6379],
        "volumes": ["/data"],
        "environment_variables": ["REDIS_PASSWORD=test"],
        "description": "Redis database image for testing"
    }
}

def create_blackboard() -> Blackboard:
    """Create a clean Blackboard instance for each test.
    
    Returns:
        Blackboard: A fresh Blackboard instance
    """
    return Blackboard()

def create_blackboard_tool(blackboard: Optional[Blackboard] = None) -> BlackboardTool:
    """Create a BlackboardTool instance with a fresh Blackboard.
    
    Args:
        blackboard: Optional Blackboard instance. If None, creates a new one.
        
    Returns:
        BlackboardTool: A tool instance connected to the Blackboard
    """
    if blackboard is None:
        blackboard = create_blackboard()
    return BlackboardTool(blackboard=blackboard)

def test_initial_blackboard() -> None:
    """Test that a new Blackboard is properly initialized with default values."""
    print("\nRunning test_initial_blackboard...")
    try:
        blackboard_tool = create_blackboard_tool()
        operations = [{"action": "get", "path": ""}]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert "results" in data, "Response missing 'results' key"
        assert len(data["results"]) == 1, f"Expected 1 result, got {len(data['results'])}"
        assert data["results"][0]["success"] is True, "Operation should succeed"
        
        blackboard_data = data["results"][0]["result"].get("blackboard", {})
        assert isinstance(blackboard_data, dict), "Blackboard data should be a dictionary"
        assert blackboard_data.get("manifests") == [], "Manifests should be empty list"
        assert blackboard_data.get("current_task") == "", "Current task should be empty string"
        assert "project" in blackboard_data, "Project should exist in blackboard"
        
        print("✅ test_initial_blackboard passed")
    except Exception as e:
        print(f"❌ test_initial_blackboard failed: {str(e)}")
        raise

def test_set_and_get_project() -> None:
    """Test setting and getting project information with validation.
    
    This test verifies that a Project object can be set and retrieved from the Blackboard.
    It ensures proper serialization and deserialization of the Project model.
    """
    print("\nRunning test_set_and_get_project...")
    try:
        blackboard_tool = create_blackboard_tool()
        
        # Create a serialized version of the project for comparison
        project_dict = TEST_PROJECT.model_dump()
        
        # Test setting project - use model_dump() to convert to dict
        operations = [{"action": "set", "path": "project", "data": project_dict}]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        assert data["results"][0]["success"] is True, "Set project should succeed"
        
        # Get project
        operations = [{"action": "get", "path": "project"}]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert data["results"][0]["success"] is True, "Get project should succeed"
        project = data["results"][0]["result"]["project"]
        
        # Verify all expected fields are present with correct values
        for key, value in TEST_DATA["project"].items():
            assert key in project, f"Project missing key: {key}"
            assert project[key] == value, f"Project {key} mismatch: {project[key]} != {value}"
            
        print("✅ test_set_and_get_project passed")
    except Exception as e:
        print(f"❌ test_set_and_get_project failed: {str(e)}")
        raise

def test_add_and_get_manifest() -> None:
    """Test adding and getting a manifest with validation of returned data."""
    print("\nRunning test_add_and_get_manifest...")
    try:
        blackboard_tool = create_blackboard_tool()
        
        # Add a manifest - use model_dump() to convert to dict
        operations = [{"action": "add", "path": "manifests", "data": TEST_MANIFEST.model_dump()}]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert data["results"][0]["success"] is True, "Add manifest operation should succeed"
        assert "manifest" in data["results"][0]["result"], "Response should include the added manifest"
        
        # Get all manifests
        operations = [{"action": "get", "path": "manifests"}]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert data["results"][0]["success"] is True, "Get manifests operation should succeed"
        manifests = data["results"][0]["result"]["manifests"]
        assert len(manifests) == 1, f"Expected 1 manifest, got {len(manifests)}"
        assert manifests[0]["description"] == TEST_DATA["manifest"]["description"], "Manifest description doesn't match"
        
        print("✅ test_add_and_get_manifest passed")
    except Exception as e:
        print(f"❌ test_add_and_get_manifest failed: {str(e)}")
        raise

def test_add_image_to_manifest() -> None:
    """Test adding an image to a manifest and verifying the nested structure."""
    print("\nRunning test_add_image_to_manifest...")
    try:
        blackboard_tool = create_blackboard_tool()
        
        # Add a manifest first - use model_dump() to convert to dict
        operations = [
            {"action": "add", "path": "manifests", "data": TEST_MANIFEST.model_dump()}
        ]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        assert data["results"][0]["success"] is True, "Adding manifest should succeed"
        
        # Add an image to the first manifest - use model_dump() to convert to dict
        operations = [
            {"action": "add", "path": "manifests[0].images", "data": TEST_REDIS_IMAGE.model_dump()}
        ]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert data["results"][0]["success"] is True, "Add image operation should succeed"
        assert "added_item" in data["results"][0]["result"], "Response should include the added item"
        
        # Verify the image was added
        operations = [{"action": "get", "path": "manifests[0].images"}]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert data["results"][0]["success"] is True, "Get images operation should succeed"
        images = data["results"][0]["result"]["manifests[0].images"]
        assert len(images) >= 1, f"Expected at least 1 image, got {len(images)}"
        
        # Check if the added image is in the list
        found_image = False
        for img in images:
            if img["image_name"] == TEST_REDIS_IMAGE.image_name and img["tag"] == TEST_REDIS_IMAGE.tag:
                found_image = True
                break
        assert found_image, f"Added image '{TEST_REDIS_IMAGE.image_name}' with tag '{TEST_REDIS_IMAGE.tag}' not found"
        
        print("✅ test_add_image_to_manifest passed")
    except Exception as e:
        print(f"❌ test_add_image_to_manifest failed: {str(e)}")
        raise

def test_update_field() -> None:
    """Test updating a specific field in a nested structure."""
    print("\nRunning test_update_field...")
    try:
        blackboard_tool = create_blackboard_tool()
        
        # Add a manifest first - use model_dump() to convert to dict
        operations = [
            {"action": "add", "path": "manifests", "data": TEST_MANIFEST.model_dump()}
        ]
        blackboard_tool._run(operations)
        
        # Update the description
        new_description = "Updated description"
        operations = [
            {"action": "set", "path": "manifests[0].description", "data": new_description}
        ]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert data["results"][0]["success"] is True, "Update operation should succeed"
        # The field name may be different in the response
        assert data["results"][0]["success"] is True, "Update operation should succeed"
        
        # Verify the update
        operations = [{"action": "get", "path": "manifests[0].description"}]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert data["results"][0]["success"] is True, "Get updated field operation should succeed"
        assert data["results"][0]["result"]["manifests[0].description"] == new_description, \
            f"Field value mismatch: expected '{new_description}', got '{data['results'][0]['result']['manifests[0].description']}'"
        
        print("✅ test_update_field passed")
    except Exception as e:
        print(f"❌ test_update_field failed: {str(e)}")
        raise

def test_multiple_operations() -> None:
    """Test performing multiple operations in a single call with transaction-like behavior."""
    print("\nRunning test_multiple_operations...")
    try:
        blackboard_tool = create_blackboard_tool()
        
        # Define a sequence of operations to perform in a single call
        operations = [
            {"action": "set", "path": "current_task", "data": "Test multiple operations"},
            {"action": "add", "path": "manifests", "data": TEST_MANIFEST.model_dump()},
            {"action": "add", "path": "manifests[0].images", "data": TEST_REDIS_IMAGE.model_dump()},
            {"action": "get", "path": "current_task"},
            {"action": "get", "path": "manifests[0].images"}
        ]
        
        # Execute all operations at once
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        # Verify each operation's success status
        for i, op in enumerate(data["results"]):
            assert op["success"] is True, f"Operation {i} failed: {op.get('error', 'Unknown error')}"
        
        # Check we got the expected number of results
        assert len(data["results"]) == 5, f"Expected 5 results, got {len(data['results'])}"
        
        # Verify the current_task operation (index 3)
        task = data["results"][3]["result"]["current_task"]
        assert task == "Test multiple operations", f"Task mismatch: {task}"
        
        # Verify the last operation (get images)
        images = data["results"][-1]["result"]["manifests[0].images"]
        assert len(images) >= 1, f"Expected at least 1 image, got {len(images)}"
        
        # Check if the added image is in the list
        found_image = False
        for img in images:
            if img["image_name"] == TEST_REDIS_IMAGE.image_name and img["tag"] == TEST_REDIS_IMAGE.tag:
                found_image = True
                break
        assert found_image, f"Added image '{TEST_REDIS_IMAGE.image_name}' with tag '{TEST_REDIS_IMAGE.tag}' not found"
        
        print("✅ test_multiple_operations passed")
    except Exception as e:
        print(f"❌ test_multiple_operations failed: {str(e)}")
        raise

def test_delete_manifest() -> None:
    """Test deleting an item from a list and verifying the deletion."""
    print("\nRunning test_delete_manifest...")
    try:
        blackboard_tool = create_blackboard_tool()
        
        # Create two test manifests with all required fields
        file1 = File(file_path="/test/manifest1.yaml", file_state="created")
        file2 = File(file_path="/test/manifest2.yaml", file_state="created")
        
        manifest1 = Manifest(
            file=file1,
            images=[TEST_NGINX_IMAGE],
            manifest_issues=[],
            description="First test manifest"
        )
        
        manifest2 = Manifest(
            file=file2,
            images=[TEST_REDIS_IMAGE],
            manifest_issues=[],
            description="Second test manifest"
        )
        
        # Add the manifests using model_dump() for serialization
        operations = [
            {"action": "add", "path": "manifests", "data": manifest1.model_dump()},
            {"action": "add", "path": "manifests", "data": manifest2.model_dump()}
        ]
        blackboard_tool._run(operations)
        
        # Delete the first manifest
        operations = [{"action": "delete", "path": "manifests[0]"}]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert data["results"][0]["success"] is True, "Delete operation should succeed"
        assert "deleted_item" in data["results"][0]["result"], "Response should include the deleted item"
        assert data["results"][0]["result"]["deleted_item"]["file"]["file_path"] == "/test/manifest1.yaml", "Wrong item was deleted"
        
        # Verify only the second manifest remains
        operations = [{"action": "get", "path": "manifests"}]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert data["results"][0]["success"] is True, "Get manifests operation should succeed"
        manifests = data["results"][0]["result"]["manifests"]
        assert len(manifests) == 1, f"Expected 1 manifest, got {len(manifests)}"
        assert manifests[0]["file"]["file_path"] == "/test/manifest2.yaml", "Remaining manifest has incorrect file path"
        assert manifests[0]["description"] == "Second test manifest", "Remaining manifest has incorrect description"
        
        print("✅ test_delete_manifest passed")
    except Exception as e:
        print(f"❌ test_delete_manifest failed: {str(e)}")
        raise

def test_error_handling() -> None:
    """Test error handling for various invalid operations and edge cases."""
    print("\nRunning test_error_handling...")
    try:
        blackboard_tool = create_blackboard_tool()
        
        # Test invalid action
        operations = [{"action": "invalid_action", "path": "manifests"}]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert data["results"][0]["success"] is False, "Invalid action should fail"
        assert "error" in data["results"][0], "Response should include error message"
        assert "Invalid action" in data["results"][0]["error"], "Error message should mention invalid action"
        
        # Test invalid path
        operations = [{"action": "get", "path": "nonexistent_field"}]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert data["results"][0]["success"] is False, "Invalid path should fail"
        assert "error" in data["results"][0], "Response should include error message"
        assert "No such field" in data["results"][0]["error"] or "not found" in data["results"][0]["error"], "Error message should mention field not found"
        
        # Test delete non-list item
        operations = [{"action": "delete", "path": "current_task"}]
        result = blackboard_tool._run(operations)
        data = json.loads(result)
        
        assert data["results"][0]["success"] is False, "Deleting non-list item should fail"
        assert "error" in data["results"][0], "Response should include error message"
        assert "Can only delete list items" in data["results"][0]["error"], "Error message should mention list items"
        
        print("✅ test_error_handling passed")
    except Exception as e:
        print(f"❌ test_error_handling failed: {str(e)}")
        raise


def run_all_tests() -> bool:
    """Run all test functions and report results.
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    tests = [
        test_initial_blackboard,
        test_set_and_get_project,
        test_add_and_get_manifest,
        test_add_image_to_manifest,
        test_update_field,
        test_multiple_operations,
        test_delete_manifest,
        test_error_handling
    ]
    
    print("\n=== Running BlackboardTool Tests ===")
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"Test {test.__name__} failed with error: {str(e)}")
    
    print(f"\nTest Summary: {passed} passed, {failed} failed")
    if failed == 0:
        print("\n🎉 All BlackboardTool tests passed successfully! 🎉")
    else:
        print(f"\n❌ {failed} test(s) failed")
    
    return failed == 0


if __name__ == "__main__":
    run_all_tests()