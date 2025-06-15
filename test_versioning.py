from __future__ import annotations
"""test_versioning.py

A minimal, easy-to-follow demonstration script that exercises the
file-versioning tools registered in ``src.services_registry.services``.

The flow:
1. Configure the repository folder (``temp``).
2. Initialise the service registry so all tools become available.
3. Create a new file.
4. Edit that file.
5. Show the version history.
6. Show a diff between the two versions.
7. Restore the file back to the first version and print the final content.

Run this file from the *root* of the project (same folder that contains
``src``).  No external arguments are needed – simply execute::

    python test_versioning.py

Nothing here is complicated: the purpose is to show the basic lifecycle
(create → edit → diff → restore) using the higher-level tools so that you
can adapt the pattern in your own code.
"""
from pathlib import Path
from pprint import pprint
import os

from typing import Any

# Import the service registry helpers.
from src.services_registry import services


def main() -> None:  # noqa: D401 – imperative mood is fine here
    """Run the demo sequence for the version-control helper tools."""

    # ------------------------------------------------------------------
    # 1. Prepare the *temp* repo directory and point the tools at it.
    # ------------------------------------------------------------------
    repo_dir = Path("temp")
    repo_dir.mkdir(exist_ok=True)
    # The tools registered in ``services`` look for this variable.
    os.environ["TEMP_FILES_DIR"] = str(repo_dir)

    # ------------------------------------------------------------------
    # 2. Initialise the service registry and retrieve the tools we need.
    # ------------------------------------------------------------------
    services.init_services()

    file_create = services.get("file_create")
    file_edit = services.get("file_edit")
    file_history = services.get("file_version_history")
    file_diff = services.get("file_version_diff")
    file_restore = services.get("file_version_restore")
    file_read = services.get("file_read")

    demo_file: str = "demo2.txt"

    # ------------------------------------------------------------------
    # 3. Create a brand-new file and commit it.
    # ------------------------------------------------------------------
    print("\n# 3. Create new file")
    create_result: dict[str, Any] = file_create.run(
        file_path=demo_file,
        content="Hello, version 1!",
        comment="Initial commit – add demo file",
    )
    pprint(create_result)

    # ------------------------------------------------------------------
    # 4. Edit the file and commit the change.
    # ------------------------------------------------------------------
    print("\n# 4. Modify file")
    edit_result: dict[str, Any] = file_edit.run(
        file_path=demo_file,
        content="Hello, version 2!",
        comment="Second revision – update greeting",
    )
    pprint(edit_result)

    # ------------------------------------------------------------------
    # 5. Show the commit history for the file.
    # ------------------------------------------------------------------
    print("\n# 5. Version history")
    history_result: dict[str, Any] = file_history.run(file_path=demo_file)
    pprint(history_result)

    # ------------------------------------------------------------------
    # 6. Diff between the two most-recent versions.
    # ------------------------------------------------------------------
    if history_result.get("success") and history_result.get("version_count", 0) >= 2:
        print("\n# 6. Diff between v1 and v2")
        diff_result: dict[str, Any] = file_diff.run(
            file_path=demo_file,
            old_version_index=1,  # first commit
            new_version_index=0,  # second commit (latest)
        )
        pprint(diff_result)

        # --------------------------------------------------------------
        # 7. Restore the file back to *v1* and inspect the content.
        # --------------------------------------------------------------
        print("\n# 7. Restore to v1")
        restore_result: dict[str, Any] = file_restore.run(
            file_path=demo_file,
            version_index=1,
        )
        pprint(restore_result)

        print("\n# 8. File content after restore")
        read_result: dict[str, Any] = file_read.run(file_path=demo_file)
        pprint(read_result)
    else:
        print("\nNot enough history to perform diff/restore steps.")


if __name__ == "__main__":
    main()
