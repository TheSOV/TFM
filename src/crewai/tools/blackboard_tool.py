"""
Blackboard Tool for CrewAI

This module provides a simple tool for manipulating the Blackboard in the DevOps flow
through the CrewAI framework. It allows getting, setting, adding, and deleting
fields in the Blackboard using a path-based approach.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Type, get_origin, get_args

from pydantic import BaseModel, Field

from crewai.tools import BaseTool
from src.crewai.devops_flow.blackboard.Blackboard import Blackboard

logger = logging.getLogger(__name__)

class BlackboardToolInput(BaseModel):
    """
    Input schema for Blackboard tool.
    
    This schema defines the input format for the BlackboardTool, which allows
    performing multiple operations on the Blackboard in a single call.
    
    Attributes:
        operations: List of operations to perform on the Blackboard.
    """
    operations: List[Dict[str, Any]] = Field(
        ...,
        description="List of operations to perform on the Blackboard. "
                  "Each operation is a dictionary with keys: 'action', 'path', and optionally 'data'."
    )

class BlackboardTool(BaseTool):
    """
    Tool to manipulate the Blackboard in the DevOps flow.
    
    This tool allows getting, setting, adding, or deleting fields in the Blackboard
    with a simple path-based approach. Multiple operations can be performed in a single call.
    
    Available actions:
    - 'get': Retrieve data from the Blackboard
    - 'set': Update existing data in the Blackboard
    - 'add': Add new items to lists in the Blackboard
    - 'delete': Remove items from the Blackboard
    
    Available paths (examples):
    - 'current_task': The current task being executed
    - 'project': Project information
    - 'general_info': General cluster information
    - 'manifests': List of all Kubernetes manifests
    - 'manifests[0]': First manifest in the list
    - 'manifests[0].images': List of images in the first manifest
    - 'manifests[0].images[1]': Second image in the first manifest
    - 'manifests[0].issues': List of issues in the first manifest
    - 'records': List of activity records
    """
    name: str = "blackboard_tool"
    args_schema: Type[BaseModel] = BlackboardToolInput
    description: str = (
        "A tool to inspect and manipulate a shared 'blackboard' state where agents collaborate. "
        "It allows reading, writing, and updating information using a simple path-based syntax. "
        "Multiple operations can be performed atomically in a single call.\n\n"
        "--- ACTIONS ---\n"
        "- get: Retrieve data from a given path.\n"
        "- set: Overwrite data at a given path.\n"
        "- add: Add a new item to a list.\n"
        "- delete: Remove an item from a list (e.g., 'manifests[0]').\n\n"
        "--- PATH SYNTAX ---\n"
        "Paths use dot notation for objects and square brackets for list indices.\n"
        "e.g., 'project.user_request', 'manifests[0]', 'manifests[0].images'.\n\n"
        "--- BLACKBOARD STRUCTURE ---\n"
        "- project: High-level project details. (e.g., 'project.user_request')\n"
        "- manifests: List of deployment manifests. (e.g., 'manifests[0].description')\n"
        "- current_task: A string describing the current agent's task.\n\n"
        "--- EXAMPLES ---\n\n"
        "# Get the project's objective\n"
        '{"operations": [{"action": "get", "path": "project.project_objective"}]}\n\n'
        "# Add a new manifest\n"
        '{"operations": [{"action": "add", "path": "manifests", "data": {\n'
        '    "file": {"file_path": "/k8s/app.yaml", "file_state": "new"},\n'
        '    "description": "Main application manifest"\n'
        '}}}]}\n\n'
        "# Add a new image to the first manifest\n"
        '{"operations": [{"action": "add", "path": "manifests[0].images", "data": {\n'
        '    "image_name": "nginx", "tag": "1.25"\n'
        '}}}]}\n\n'
        "# Perform multiple operations (add a manifest and set the current task)\n"
        '{"operations": [\n'
        '    {"action": "add", "path": "manifests", "data": {"description": "DB manifest"}},\n'
        '    {"action": "set", "path": "current_task", "data": "Deploying database"}\n'
        ']}\n\n'
        "Note: If any operation in a multi-operation call fails, all changes are discarded."
    )
    args_schema: Type[BaseModel] = BlackboardToolInput
    
    # The Blackboard instance (excluded from serialization)
    blackboard: Blackboard = Field(..., exclude=True, description="The Blackboard instance to manipulate")

    def __init__(self, blackboard: Blackboard, **kwargs):
        """Initialize the BlackboardTool.
        
        Args:
            blackboard: The Blackboard instance to use.
            **kwargs: Additional arguments to pass to the parent class.
        """
        super().__init__(blackboard=blackboard, **kwargs)
        # It's already stored by Pydantic via the field; no further assignment needed.
        
    def _run(self, operations: List[Dict[str, Any]]) -> str:
        """
        Run the specified operations on the Blackboard.
        
        Args:
            operations: List of operations to perform. Each operation is a dictionary with:
                - action: The action to perform ('get', 'set', 'add', 'delete')
                - path: The path to the field in the Blackboard
                - data: The data to set or add (for 'set' and 'add' actions)
                
        Returns:
            str: JSON string containing the results of all operations
        """
        results = []
        blackboard = self.blackboard
        
        for i, op in enumerate(operations):
            if 'action' not in op or 'path' not in op:
                results.append({
                    "operation": i,
                    "success": False,
                    "error": "Missing required fields 'action' or 'path'"
                })
                continue
            
            action = op['action']
            path = op['path']
            data = op.get('data')
            
            try:
                if action == 'get':
                    result = self._get_field(blackboard, path)
                elif action == 'set':
                    if data is None:
                        result = {"error": "Data is required for set operation"}
                    else:
                        result = self._set_field(blackboard, path, data)
                elif action == 'add':
                    if data is None:
                        result = {"error": "Data is required for add operation"}
                    else:
                        result = self._add_field(blackboard, path, data)
                elif action == 'delete':
                    result = self._delete_field(blackboard, path)
                else:
                    result = {"error": f"Invalid action: {action}"}
                
                op_result = {
                    "operation": i,
                    "action": action,
                    "path": path,
                }
                if "error" in result:
                    op_result["success"] = False
                    op_result["error"] = result["error"]
                else:
                    op_result["success"] = True
                    op_result["result"] = result
                results.append(op_result)

            except Exception as e:
                logger.error(f"Error performing {action} operation on path {path}: {str(e)}")
                results.append({
                    "operation": i,
                    "action": action,
                    "path": path,
                    "success": False,
                    "error": str(e)
                })
        
        class PydanticEncoder(json.JSONEncoder):
            def default(self, obj):
                if hasattr(obj, 'model_dump') and callable(obj.model_dump):
                    return obj.model_dump()
                return super().default(obj)

        return json.dumps({"results": results}, indent=2, cls=PydanticEncoder)
    
    def _get_field(self, blackboard: Blackboard, path: str) -> Dict[str, Any]:
        """
        Get a field from the Blackboard using a path.
        
        Args:
            blackboard: The Blackboard instance
            path: Path to the field (e.g., 'current_task', 'manifests[0].images')
            
        Returns:
            Dict[str, Any]: The requested field data or error information
        """
        try:
            # Handle empty path (return entire blackboard)
            if not path:
                return {"blackboard": self._serialize_blackboard(blackboard)}

            # Check if root-level field exists before resolving
            if '.' not in path and '[' not in path and not hasattr(blackboard, path):
                return {"error": f"Field '{path}' not found in Blackboard."}
                
            value = self._resolve_path(blackboard, path)

            if hasattr(value, 'model_dump') and callable(value.model_dump):
                return {path: value.model_dump()}
            elif isinstance(value, list):
                return {path: [item.model_dump() if hasattr(item, 'model_dump') else item for item in value]}
            else:
                return {path: value}

        except (AttributeError, IndexError):
            return {"error": f"Field at path '{path}' not found."}
        except Exception as e:
            return {"error": f"Failed to get field at path '{path}': {str(e)}"}
    
    @staticmethod
    def _get_field_type(parent: Any, attr_name: str) -> Optional[Type[Any]]:
        """Return the annotated type of *attr_name* for *parent* if available."""
        return getattr(parent.__class__, "__annotations__", {}).get(attr_name)

    @staticmethod
    def _get_list_element_type(parent: Any, attr_name: str) -> Optional[Type[Any]]:
        """Infer the element type of a list attribute using type hints.

        Args:
            parent: The object owning the attribute.
            attr_name: The attribute name to inspect.

        Returns:
            The element type if it can be determined, otherwise ``None``.
        """
        field_type = BlackboardTool._get_field_type(parent, attr_name)
        if field_type is None:
            return None
        origin = get_origin(field_type)
        if origin in (list, List):
            args = get_args(field_type)
            if args:
                return args[0]
        return None

    def _set_field(self, blackboard: Blackboard, path: str, data: Any) -> Dict[str, Any]:
        """
        Set a field in the Blackboard using a path.
        
        Args:
            blackboard: The Blackboard instance
            path: Path to the field (e.g., 'current_task', 'manifests[0].description')
            data: Data to set
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        try:
            # Check if this is a root-level field
            if '.' not in path and '[' not in path:
                # Get the field info to determine the type
                field_info = Blackboard.model_fields.get(path)
                if field_info is None:
                    raise ValueError(f"No such field: {path}")
                
                # Handle different field types
                field_type = field_info.annotation
                if field_type == str:
                    setattr(blackboard, path, data)
                elif hasattr(field_type, 'model_validate'):
                    # For Pydantic models, convert dict to model if needed
                    try:
                        value = field_type.model_validate(data) if isinstance(data, dict) else data
                        setattr(blackboard, path, value)
                    except Exception as e:
                        return {"error": f"Failed to validate data for field '{path}': {str(e)}"}
                else:
                    setattr(blackboard, path, data)
                
                # Return the updated field
                return {path: getattr(blackboard, path)}
            
            # For nested paths, parse the path to get parent object and attribute name
            parent, attr_name, is_list_item, index = self._parse_path(blackboard, path)
            
            if is_list_item:
                # Setting a list item
                try:
                    attr_list: List[Any] = getattr(parent, attr_name)
                    element_type = self._get_list_element_type(parent, attr_name)
                    if isinstance(data, dict) and isinstance(element_type, type) and issubclass(element_type, BaseModel):
                        attr_list[index] = element_type.model_validate(data)
                    else:
                        attr_list[index] = data
                except Exception as e:
                    return {"error": f"Failed to set list item at index {index}: {str(e)}"}
            else:
                # Setting a regular attribute
                field_type = self._get_field_type(parent, attr_name)
                try:
                    if isinstance(data, dict) and isinstance(field_type, type) and issubclass(field_type, BaseModel):
                        setattr(parent, attr_name, field_type.model_validate(data))
                    else:
                        setattr(parent, attr_name, data)
                except Exception as e:
                    return {"error": f"Failed to set field '{attr_name}': {str(e)}"}
            
            return {"success": True, "path": path}
            
        except Exception as e:
            return {"error": f"Failed to set field at path '{path}': {str(e)}"}
    
    def _add_field(self, blackboard: Blackboard, path: str, data: Any) -> Dict[str, Any]:
        """
        Add an item to a list in the Blackboard.
        """
        try:
            # Resolve the target list
            target_list = self._resolve_path(blackboard, path)
            if not isinstance(target_list, list):
                return {"error": f"Path '{path}' does not point to a list."}

            # Determine the parent object and attribute name to get type hints
            if '.' not in path and '[' not in path:
                parent = blackboard
                attr_name = path
            else:
                last_dot_pos = path.rfind('.')
                if last_dot_pos == -1:
                    return {"error": f"Invalid path for add operation: '{path}'. Path must point to a list attribute."}
                
                parent_path = path[:last_dot_pos]
                attr_name = path[last_dot_pos + 1:]
                parent = self._resolve_path(blackboard, parent_path)

            element_type = self._get_list_element_type(parent, attr_name)
            
            if isinstance(data, dict) and isinstance(element_type, type) and issubclass(element_type, BaseModel):
                new_item = element_type.model_validate(data)
            else:
                new_item = data
            
            target_list.append(new_item)
            
            response_data = new_item.model_dump() if hasattr(new_item, "model_dump") else new_item
            
            if '.' not in path and '[' not in path:
                key_name = path.rstrip("s")
                return {"index": len(target_list) - 1, key_name: response_data}
            else:
                return {"index": len(target_list) - 1, "added_item": response_data}

        except Exception as e:
            return {"error": f"Failed to add item to list at path '{path}': {str(e)}"}
    
    def _delete_field(self, blackboard: Blackboard, path: str) -> Dict[str, Any]:
        """
        Delete a field from the Blackboard using a path.
        
        Args:
            blackboard: The Blackboard instance
            path: Path to the field to delete (e.g., 'manifests[0]', 'records[1]')
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        try:
            # We only allow deleting list items, not attributes
            if '[' not in path or not path.endswith(']'):
                return {"error": "Can only delete list items, not attributes"}
            
            parent, attr_name, is_list_item, index = self._parse_path(blackboard, path)
            
            if not is_list_item:
                return {"error": f"Path '{path}' does not point to a list item"}
            
            # Get the list and check if the index is valid
            attr_list = getattr(parent, attr_name)
            if not 0 <= index < len(attr_list):
                return {"error": f"Index {index} out of range for list at path '{path}'"}
            
            # Delete the item and return it
            deleted_item = attr_list.pop(index)
            if hasattr(deleted_item, 'model_dump') and callable(deleted_item.model_dump):
                return {"deleted_item": deleted_item.model_dump()}
            return {"deleted_item": deleted_item}
            
        except Exception as e:
            return {"error": f"Failed to delete field at path '{path}': {str(e)}"}
    
    def _resolve_path(self, obj: Any, path: str) -> Any:
        """
        Resolve a path to an object or value in the Blackboard.
        
        Args:
            obj: The object to start from (usually the Blackboard)
            path: Path to resolve (e.g., 'manifests[0].images[1].name')
            
        Returns:
            Any: The resolved object or value
        """
        if not path:
            return obj
            
        components = path.split('.')
        current = obj
        
        for comp in components:
            if '[' in comp and comp.endswith(']'):
                # Handle list indexing
                name, index_str = comp.split('[', 1)
                index = int(index_str[:-1])
                
                if name:
                    # Get the list attribute first
                    current = getattr(current, name)
                    
                # Then get the indexed item
                current = current[index]
            else:
                # Regular attribute access
                current = getattr(current, comp)
                
        return current
    
    def _parse_path(self, obj: Any, path: str) -> Tuple[Any, str, bool, Optional[int]]:
        """
        Parse a path to get the parent object, attribute name, and index if applicable.
        
        Args:
            obj: The object to start from (usually the Blackboard)
            path: Path to parse (e.g., 'manifests[0].images[1].name')
            
        Returns:
            tuple: (parent_object, attribute_name, is_list_item, index)
        """
        # Check if this is a list item path (ends with [n])
        if '[' in path and path.endswith(']'):
            last_dot = path.rfind('.')
            
            if last_dot == -1:
                # This is a top-level list like 'manifests[0]'
                attr_name = path[:path.index('[')]
                index_str = path[path.index('[') + 1:path.rindex(']')]
                index = int(index_str)
                return obj, attr_name, True, index
            else:
                # This is a nested list like 'manifests[0].images[1]'
                parent_path = path[:last_dot]
                attr_name = path[last_dot + 1:path.index('[', last_dot)]
                index_str = path[path.index('[', last_dot) + 1:path.rindex(']')]
                index = int(index_str)
                parent = self._resolve_path(obj, parent_path)
                return parent, attr_name, True, index
        
        # Handle the case of a direct attribute like 'current_task'
        if '.' not in path:
            return obj, path, False, None
        
        # Handle the case of a nested attribute like 'manifests[0].description'
        last_dot = path.rfind('.')
        parent_path = path[:last_dot]
        attr_name = path[last_dot + 1:]
        parent = self._resolve_path(obj, parent_path)
        return parent, attr_name, False, None
    
    def _serialize_blackboard(self, blackboard: Blackboard) -> Dict[str, Any]:
        """
        Serialize the entire Blackboard to a dictionary.
        
        Args:
            blackboard: The Blackboard instance
            
        Returns:
            Dict[str, Any]: Serialized Blackboard with all fields from the model
        """
        result = {}
        for field_name, field_info in blackboard.model_fields.items():
            value = getattr(blackboard, field_name, None)
            if value is None:
                result[field_name] = None
            elif isinstance(value, list):
                result[field_name] = [
                    item.model_dump() if hasattr(item, 'model_dump') else item 
                    for item in value
                ]
            elif hasattr(value, 'model_dump'):
                result[field_name] = value.model_dump()
            else:
                result[field_name] = value
                
        return result