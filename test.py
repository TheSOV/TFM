import json
from pathlib import Path
from textwrap import dedent
import os

from src.crewai.tools.yaml_tools import (
    YAMLEditTool,
    YAMLReadTool,
)

def run_yaml_test():
    """Runs a series of tests for YAML operation tools."""
    test_file = Path("test_data.yaml")

    # --- Setup: Create a multi-document YAML file ---
    print("--- Setting up YAML test environment ---")
    yaml_content = dedent("""\
        # Document 0: Server Configuration
        server:
          host: localhost
          port: 8080
        ---
        # Document 1: Database Settings
        database:
          type: postgresql
          host: db.example.com
          port: 5432
          user: default_user
        ---
        # Document 2: Feature Flags
        features:
          new_dashboard: true
          api_versioning: false
    """)
    test_file.write_text(yaml_content)
    print(f"Created temporary file: {test_file}")

    # --- Instantiate Tools ---
    read_tool = YAMLReadTool(file_path=test_file)
    edit_tool = YAMLEditTool(file_path=test_file)

    try:
        # --- 1. Read All Documents ---
        print("\n--- 1. Reading all YAML documents ---")
        all_docs_str = read_tool._run()
        all_docs = json.loads(all_docs_str)
        assert len(all_docs) == 3, f"Expected 3 documents, but found {len(all_docs)}"
        assert all_docs[1]['document']['database']['host'] == 'db.example.com', "Content mismatch in document 1"
        print("Read all documents verified.")

        # --- 2. Read a Specific Document ---
        print("\n--- 2. Reading a specific YAML document (index 1) ---")
        doc1_str = read_tool._run(document_index=1)
        doc1 = json.loads(doc1_str)
        assert doc1['database']['port'] == 5432, "Content mismatch when reading specific document"
        print("Read specific document verified.")

        # --- 3. Edit: Add, Replace, and Delete keys ---
        print("\n--- 3. Editing YAML: Add, Replace, Delete ---")
        operations = [
            {'key': 'server.timeout', 'operation': 'add', 'value': 60, 'document_index': 0},
            {'key': 'database.user', 'operation': 'replace', 'value': 'admin', 'document_index': 1},
            {'key': 'features.api_versioning', 'operation': 'delete', 'document_index': 2},
        ]
        result = edit_tool._run(operations=operations, comment="Perform various edits")
        assert "✅" in result, f"Edit operation failed: {result}"
        
        # Verify changes
        doc0_str = read_tool._run(document_index=0)
        doc0 = json.loads(doc0_str)
        assert doc0['server']['timeout'] == 60, "Add operation failed to verify"
        doc1_str = read_tool._run(document_index=1)
        doc1 = json.loads(doc1_str)
        assert doc1['database']['user'] == 'admin', "Replace operation failed to verify"
        doc2_str = read_tool._run(document_index=2)
        doc2 = json.loads(doc2_str)
        assert 'api_versioning' not in doc2['features'], "Delete operation failed to verify"
        print("Add, Replace, and Delete operations verified.")

        # --- 4. Edit: Add a dictionary ---
        print("\n--- 4. Editing YAML: Add a dictionary object ---")
        new_feature = {'name': 'beta_feature', 'enabled': True}
        operations = [
            {'key': 'features.new_feature', 'operation': 'add', 'value': new_feature, 'document_index': 2},
        ]
        result = edit_tool._run(operations=operations, comment="Add a dictionary")
        assert "✅" in result, f"Add dictionary operation failed: {result}"
        
        # Verify change
        doc2_str = read_tool._run(document_index=2)
        doc2 = json.loads(doc2_str)
        assert doc2['features']['new_feature']['name'] == 'beta_feature', "Add dictionary failed to verify"
        print("Add dictionary operation verified.")

        print("Add dictionary operation verified.")

        # --- 5. Create a new file from scratch ---
        print("\n--- 5. Creating a new YAML file from scratch ---")
        new_file_path = Path("new_test_file.yaml")
        if new_file_path.exists():
            new_file_path.unlink()
        
        create_tool = YAMLEditTool(file_path=new_file_path)
        operations = [
            {'operation': 'add_document', 'value': {'service': {'name': 'auth-service', 'version': '1.0'}}},
            {'operation': 'add_document', 'value': {'config': {'retries': 3, 'timeout': 5000}}},
        ]
        result = create_tool._run(operations=operations, comment="Create file with two documents")
        assert "✅" in result, f"File creation operation failed: {result}"

        # Verify file content
        read_new_tool = YAMLReadTool(file_path=new_file_path)
        all_docs_str = read_new_tool._run()
        all_docs = json.loads(all_docs_str)
        assert len(all_docs) == 2, "File creation did not result in 2 documents"
        assert all_docs[0]['document']['service']['name'] == 'auth-service', "Content mismatch in newly created file"
        print("File creation from scratch verified.")

        # --- 6. Edit: Modify a nested list item ---
        print("\n--- 6. Editing YAML: Modify a nested list item ---")
        nested_list_file = Path("test_nested_list.yaml")
        nested_list_content = dedent("""\
            # Document 0: RBAC Rules
            kind: ClusterRole
            apiVersion: rbac.authorization.k8s.io/v1
            metadata:
              name: test-role
            rules:
              - apiGroups: ["", "apps"]
                resources: ["pods", "deployments"]
                verbs: ["get", "list", "watch"]
              - apiGroups: ["batch"]
                resources: ["jobs"]
                verbs: ["get", "list", "watch", "create"]
        """)
        nested_list_file.write_text(nested_list_content)
        
        nested_edit_tool = YAMLEditTool(file_path=nested_list_file)
        operations = [
            {'key': 'rules.0.apiGroups', 'operation': 'replace', 'value': ['v1'], 'document_index': 0},
        ]
        result = nested_edit_tool._run(operations=operations, comment="Modify nested list")
        assert "✅" in result, f"Nested list edit operation failed: {result}"

        # Verify change
        nested_read_tool = YAMLReadTool(file_path=nested_list_file)
        doc_str = nested_read_tool._run(document_index=0)
        doc = json.loads(doc_str)
        assert doc['rules'][0]['apiGroups'] == ['v1'], "Nested list edit failed to verify"
        print("Nested list item modification verified.")

        # --- 7. Edit: Delete a document ---
        print("\n--- 7. Editing YAML: Delete a document ---")
        operations = [
            {'operation': 'delete_document', 'document_index': 1},
        ]
        result = edit_tool._run(operations=operations, comment="Delete document 1")
        assert "✅" in result, f"Delete document operation failed: {result}"

        # Verify change
        all_docs_str = read_tool._run()
        all_docs = json.loads(all_docs_str)
        assert len(all_docs) == 2, f"Expected 2 documents after deletion, but found {len(all_docs)}"
        assert all_docs[0]['document']['server']['host'] == 'localhost', "Document 0 content mismatch after deletion"
        assert all_docs[1]['document']['features']['new_dashboard'] == True, "Document 1 (originally 2) content mismatch after deletion"
        print("Delete document operation verified.")

        # --- 8. Edit: Prevent Adding Duplicate Kubernetes Manifest ---
        print("\n--- 8. Editing YAML: Prevent Adding Duplicate Kubernetes Manifest ---")
        k8s_test_file = Path("test_k8s_duplicates.yaml")
        
        # Initial manifest
        k8s_manifest_content = dedent("""\
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: my-app
              namespace: default
            spec:
              replicas: 1
        """)
        k8s_test_file.write_text(k8s_manifest_content)

        k8s_edit_tool = YAMLEditTool(file_path=k8s_test_file)
        k8s_read_tool = YAMLReadTool(file_path=k8s_test_file)

        # Duplicate manifest to attempt to add
        duplicate_manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "my-app",
                "namespace": "default"
            },
            "spec": {
                "replicas": 2 # Different spec, but same identity
            }
        }

        # --- 8a. Attempt to add the duplicate ---
        print("--- 8a. Attempting to add a duplicate manifest (should fail) ---")
        operations = [
            {'operation': 'add_document', 'value': duplicate_manifest},
        ]
        result = k8s_edit_tool._run(operations=operations, comment="Attempt to add duplicate")
        
        assert "Error editing YAML file: Cannot add duplicate manifest" in result, f"Duplicate check failed. Got: {result}"
        print("Verified that adding a duplicate manifest fails as expected.")

        # Verify that the file was not changed
        all_docs_str = k8s_read_tool._run()
        all_docs = json.loads(all_docs_str)
        assert len(all_docs) == 1, f"File should have 1 document after failed duplicate add, but has {len(all_docs)}"
        print("Verified that the file content remains unchanged after a failed operation.")

        # --- 8b. Add a non-duplicate manifest ---
        print("\n--- 8b. Adding a non-duplicate manifest (should succeed) ---")
        non_duplicate_manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": "my-app-service",
                "namespace": "default"
            }
        }
        operations = [
            {'operation': 'add_document', 'value': non_duplicate_manifest},
        ]
        result = k8s_edit_tool._run(operations=operations, comment="Add a valid new manifest")
        assert "✅" in result, f"Adding a non-duplicate manifest failed: {result}"

        # Verify the new document was added
        all_docs_str = k8s_read_tool._run()
        all_docs = json.loads(all_docs_str)
        assert len(all_docs) == 2, f"Expected 2 documents after adding a new one, but found {len(all_docs)}"
        assert all_docs[1]['document']['kind'] == 'Service', "The new document was not added correctly."
        print("Verified that a non-duplicate manifest can be added successfully.")


        print("\n--- All YAML tests passed successfully! ---")

    finally:
        # --- Cleanup ---
        print("\n--- Cleaning up YAML test environment ---")
        if test_file.exists():
            test_file.unlink()
            print(f"Removed temporary file: {test_file}")
        if 'new_file_path' in locals() and new_file_path.exists():
            new_file_path.unlink()
            print(f"Removed temporary file: {new_file_path}")
        if 'nested_list_file' in locals() and nested_list_file.exists():
            nested_list_file.unlink()
            print(f"Removed temporary file: {nested_list_file}")
        if 'k8s_test_file' in locals() and k8s_test_file.exists():
            k8s_test_file.unlink()
            print(f"Removed temporary file: {k8s_test_file}")

if __name__ == "__main__":
    run_yaml_test()
