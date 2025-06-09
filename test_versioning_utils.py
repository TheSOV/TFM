"""
Comprehensive tests for FileVersioning utility.
Each test step includes an explanation.
"""
from src.version_control.versioning_utils import FileVersioning, VersioningError
from pathlib import Path
import shutil
import os

REPO_DIR = "temp"
TEST_FILE = "nginx-deployment.yaml"

# --- Setup: Ensure a clean repo directory ---
if Path(REPO_DIR).exists():
    shutil.rmtree(REPO_DIR)
Path(REPO_DIR).mkdir()

# --- Step 1: Create a test file ---
# Explanation: We create a sample file inside the repo to track with version control.
test_file_path = Path(REPO_DIR) / TEST_FILE
with open(test_file_path, "w") as f:
    f.write("apiVersion: v1\nkind: Pod\nmetadata:\n  name: testpod\n")

# --- Step 2: Initialize the FileVersioning utility ---
# Explanation: This will create the repo if it doesn't exist.
vc = FileVersioning(REPO_DIR)

# --- Step 3: Add the file to version control ---
# Explanation: Stage the file for commit.
try:
    vc.add_file(TEST_FILE)
    print("[PASS] add_file")
except VersioningError as e:
    print(f"[FAIL] add_file: {e}")

# --- Step 4: Commit the changes ---
# Explanation: Commit the staged file to the repo.
try:
    commit_sha = vc.commit_changes("Initial commit")
    print(f"[PASS] commit_changes: {commit_sha}")
except VersioningError as e:
    print(f"[FAIL] commit_changes: {e}")

# --- Step 5: Modify the file and commit again ---
# Explanation: Make a significant change to the file for clear diff output
print("[INFO] Modifying file with significant changes...")
with open(test_file_path, "w") as f:
    f.write("apiVersion: v1\nkind: Pod\nmetadata:\n  name: testpod\nspec:\n  containers:\n  - name: nginx\n    image: nginx:latest\n    ports:\n    - containerPort: 80\n")

# Important: Must add the file again to stage changes
print("[INFO] Staging modified file...")
try:
    vc.add_file(TEST_FILE)
    print("[PASS] add_file (after modification)")
except VersioningError as e:
    print(f"[FAIL] add_file (after modification): {e}")
    
try:
    commit_sha2 = vc.commit_changes("Add nginx container configuration")
    print(f"[PASS] commit_changes (2nd): {commit_sha2}")
except VersioningError as e:
    print(f"[FAIL] commit_changes (2nd): {e}")

# --- Step 6: Get commit history for the file ---
# Explanation: Retrieve and print the commit history for the tracked file.
history = []
try:
    history = vc.get_file_history(TEST_FILE)
    print(f"[INFO] Number of commits in history: {len(history)}")
    print("[PASS] get_file_history:")
    for i, entry in enumerate(history):
        print(f"  Commit {i}: {entry}")
except VersioningError as e:
    print(f"[FAIL] get_file_history: {e}")

# --- Step 7: Get diff between the two commits ---
# Explanation: Use commit SHAs from history for diff, not symbolic refs.
try:
    if len(history) >= 2:
        # Note: In our history list, the most recent commit is at index 0
        old_sha = history[1]['sha']  # older commit (initial)
        new_sha = history[0]['sha']  # latest commit (with container config)
        print(f"[INFO] Getting diff between:\n  - {old_sha} (initial)\n  - {new_sha} (with container config)")
        
        # Add debug print to verify file path
        print(f"[DEBUG] Looking for file: {TEST_FILE} in repo: {REPO_DIR}")
        
        # Get the diff
        diff = vc.get_file_diff(TEST_FILE, old_sha, new_sha)
        print("[PASS] get_file_diff:")
        print(diff)
    else:
        print(f"[FAIL] get_file_diff: Not enough commits to diff. Full history:")
        for i, entry in enumerate(history):
            print(f"  Commit {i}: {entry}")
except VersioningError as e:
    print(f"[FAIL] get_file_diff: {e}")

# --- Step 8: Restore the file to the initial commit ---
# Explanation: Use the oldest commit SHA for restore.
try:
    if len(history) >= 2:
        # Note: In our history list, the most recent commit is at index 0
        initial_sha = history[1]['sha']  # Use the initial commit SHA
        print(f"[INFO] Restoring file to revision: {initial_sha}")
        
        # Add debug print to verify file path
        print(f"[DEBUG] Restoring file: {TEST_FILE} from revision: {initial_sha}")
        
        vc.restore_file(TEST_FILE, initial_sha)
        with open(test_file_path, "r") as f:
            restored_content = f.read()
        print("[PASS] restore_file. Restored content:")
        print(restored_content)
        
        # Verify the file was actually restored to original content
        expected_content = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: testpod\n"
        if restored_content.strip() == expected_content.strip():
            print("[PASS] Content verification: File correctly restored to original state")
        else:
            print("[FAIL] Content verification: File content doesn't match expected original state")
    else:
        print(f"[FAIL] restore_file: Not enough commits to restore. Full history:")
        for i, entry in enumerate(history):
            print(f"  Commit {i}: {entry}")
except VersioningError as e:
    print(f"[FAIL] restore_file: {e}")
