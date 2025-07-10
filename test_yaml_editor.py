import json
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List

import pytest

from src.crewai.tools.yaml_tools import (
    YAMLEditTool,
    YAMLReadTool,
)

"""End‑to‑end tests for the CrewAI YAML tools.

These tests intentionally batch multiple kinds of operations (add / replace / delete
on keys, add_document, delete_document) in different orders to make sure the tool
handles index‑shifts and duplicate‑resource validation internally, without the
agent having to care.
"""

# -----------------------------------------------------------------------------
# Helper utilities
# -----------------------------------------------------------------------------

def create_complex_yaml(tmp_path: Path) -> Path:
    """Create a multi‑document YAML file for testing."""
    content = dedent(
        """
        # Doc 0
        settings:
          enabled: true
          count: 5
        ---
        # Doc 1
        users:
          - name: alice
            roles: [admin, user]
          - name: bob
            roles: [user]
        ---
        # Doc 2
        apiVersion: v1
        kind: Service
        metadata:
          name: web
          namespace: default
        spec:
          ports:
            - port: 80
              protocol: TCP
        ---
        # Doc 3 (empty)
        ---
        # Doc 4
        tree:
          branch:
            leaves:
              - green
              - yellow
              - red
            metrics:
              height: 10
              width: 2
        """
    )
    file = tmp_path / "complex.yaml"
    file.write_text(content)
    return file


@pytest.fixture
def helper(tmp_path) -> Dict[str, Any]:
    """Return a dict holding a fresh YAML file plus read/edit tools bound to it."""
    test_file = create_complex_yaml(tmp_path)
    return {
        "file": test_file,
        "read_tool": YAMLReadTool(file_path=test_file),
        "edit_tool": YAMLEditTool(file_path=test_file),
    }


class TestYAMLEndToEnd:
    """Comprehensive, order‑agnostic tests for the YAML tools."""

    # ------------------------------------------------------------------
    # tiny wrappers so the tests read clearly
    # ------------------------------------------------------------------
    def _read(self, helper: Dict[str, Any], idx: int | None = None):
        raw = helper["read_tool"]._run(document_index=idx)
        return json.loads(raw)

    def _edit(self, helper: Dict[str, Any], ops: List[Dict], comment: str = ""):  # -> str
        return helper["edit_tool"]._run(operations=ops, comment=comment)

    # ------------------------------------------------------------------
    # 1) Mixed ops – key edits before delete_document
    # ------------------------------------------------------------------
    def test_mixed_operations_order1(self, helper):
        ops = [
            # add a new key in doc0
            {"operation": "add", "key": "settings.max", "value": 100, "document_index": 0},
            # replace bob's first role
            {"operation": "replace", "key": "users[1].roles[0]", "value": "editor", "document_index": 1},
            # delete the "red" leaf
            {"operation": "delete", "key": "tree.branch.leaves[2]", "document_index": 4},
            # remove the empty doc3
            {"operation": "delete_document", "document_index": 3},
            # append a new Deployment (duplicate‑name check comes later)
            {
                "operation": "add_document",
                "value": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {"name": "web", "namespace": "default"},
                    "spec": {"replicas": 2},
                },
            },
        ]
        result = self._edit(helper, ops, "order1")
        assert result.startswith("✅")

        # Validate doc0 change
        assert self._read(helper, 0)["settings"]["max"] == 100
        # Validate doc1 change
        assert self._read(helper, 1)["users"][1]["roles"][0] == "editor"
        # The empty doc3 was deleted, so original doc4 (tree) is now index 3
        tree_doc = self._read(helper, 3)
        assert tree_doc["tree"]["branch"]["leaves"] == ["green", "yellow"]
        # Check overall kinds layout
        kinds = [d['document'].get('kind') for d in self._read(helper)]
        assert kinds == [None, None, "Service", None, "Deployment"]

    # ------------------------------------------------------------------
    # 2) Mixed ops – delete_document first in the list (tool reorders internally)
    # ------------------------------------------------------------------
    def test_mixed_operations_order2(self, helper):
        ops = [
            {"operation": "delete_document", "document_index": 3},
            {"operation": "add", "key": "settings.min", "value": 1, "document_index": 0},
            {"operation": "replace", "key": "tree.branch.metrics.height", "value": 20, "document_index": 4},
            {"operation": "add_document", "value": {"new": {"flag": True}}},
        ]
        result = self._edit(helper, ops, "order2")
        assert result.startswith("✅")

        assert self._read(helper, 0)["settings"]["min"] == 1
        # After deletion of original doc3, tree doc is now index 3
        assert self._read(helper, 3)["tree"]["branch"]["metrics"]["height"] == 20
        # New doc appended
        assert self._read(helper)[-1]['document'] == {"new": {"flag": True}}

    # ------------------------------------------------------------------
    # 3) Duplicate resource guard – should return an Error in result string
    # ------------------------------------------------------------------
    def test_duplicate_resource_add_document_error(self, helper):
        duplicate = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "web", "namespace": "default"},
        }
        result = self._edit(helper, [{"operation": "add_document", "value": duplicate}], "dup")
        assert "Error" in result and "duplicate" in result.lower()

    # ------------------------------------------------------------------
    # 4) Error handling for bad indices / paths
    # ------------------------------------------------------------------
    def test_error_invalid_index_and_path(self, helper):
        # out‑of‑range document index
        res_idx = self._edit(helper, [{"operation": "add", "key": "foo", "value": "bar", "document_index": 42}], "bad‑idx")
        assert "Error" in res_idx
        # bad path inside existing document
        res_path = self._edit(helper, [{"operation": "replace", "key": "tree.branch.nope", "value": 0, "document_index": 4}], "bad‑path")
        assert "Error" in res_path
