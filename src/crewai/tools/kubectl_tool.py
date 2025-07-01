# kubectl_tool.py
from typing import Annotated, Set, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field, PrivateAttr
from crewai.tools import BaseTool
from src.crewai.tools.utils.safe_kubectl import SafeKubectl
import os

class KubectlArgs(BaseModel):
    """
    Input schema for the tool. The agent must pass a *full* kubectl
    command string (including the word 'kubectl').
    """
    command: Annotated[
        str,
        Field(
            description=(
                "A complete kubectl command **starting with the word "
                "'kubectl'**, e.g. `kubectl get pods -n staging`."
            )
        ),
    ]

class KubectlTool(BaseTool):
    """
    A safe wrapper around kubectl that enforces security policies.
    
    Args:
        kubectl_path: Path to the kubectl binary
        allowed_verbs: Set of allowed kubectl verbs
        safe_namespaces: Set of allowed namespaces
        deny_flags: Set of denied command-line flags
    """
    
    # CrewAI requires these class attributes
    name: str = "safe_kubectl"
    description: str = (
        "Run a kubectl CLI command with strict guard-rails. "
        "Dangerous flags and shell metacharacters are blocked."
    )
    args_schema: type[BaseModel] = KubectlArgs
    
    # Internal attributes
    kubectl: Optional[SafeKubectl] = Field(default=None, exclude=True, init=False)
    _base_dir: Path = PrivateAttr(default=Path.cwd())

    def __init__(
        self,
        kubectl_path: str = "C:\\Program Files\\Docker\\Docker\\resources\\bin\\kubectl.exe",
        allowed_verbs: Optional[Set[str]] = None,
        safe_namespaces: Optional[Set[str]] = None,
        denied_namespaces: Optional[Set[str]] = None,
        deny_flags: Optional[Set[str]] = None,
        base_dir: str = ".",
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        
        # Set base directory if provided
        self._base_dir = Path(base_dir).expanduser().resolve()
        
        # Initialize the kubectl instance
        self.kubectl = SafeKubectl(
            kubectl_path=kubectl_path,
            allowed_verbs=allowed_verbs,
            safe_namespaces=safe_namespaces,
            denied_namespaces=denied_namespaces,
            deny_flags=deny_flags
        )
        
        # Update description with current allowed verbs and namespaces
        if allowed_verbs:
            self.description += f"\nAllowed verbs: {', '.join(sorted(allowed_verbs))}"
        if safe_namespaces:
            self.description += f"\nAllowed namespaces: {', '.join(sorted(safe_namespaces))}"

    def _run(self, command: str) -> str:
        """
        Execute a kubectl command with security validations.
        
        Args:
            command: The full kubectl command string. File paths in the command will be
                   interpreted as relative to the base directory.
            
        Returns:
            str: Command output with exit code, stdout, and stderr
            
        Note:
            For commands that work with files (like 'apply -f'), the file paths must be
            relative to the base directory. Absolute paths and path traversal sequences
            (e.g., '../') are not allowed for security reasons. Paths should use
            forward slashes.
        """
        # Split the command into parts for processing
        parts = command.split()
        if not parts or parts[0].lower() != 'kubectl':
            return "Error: Command must start with 'kubectl'"
            
        # Process file paths in the command
        processed_parts = []
        i = 0
        while i < len(parts):
            part = parts[i]
            # Check for -f/--filename flags and process the next part as a file path
            if part in ('-f', '--filename') and i + 1 < len(parts):
                file_path_str = parts[i + 1]
                # Normalize the path to be relative to the base directory, preventing path traversal
                relative_path = os.path.normpath(file_path_str).replace('\\', '/').lstrip('/')
                
                # Create the full, absolute path
                full_path = (self._base_dir / relative_path).resolve()
                
                # Security check: ensure the resolved path is within the base directory
                if not str(full_path).startswith(str(self._base_dir.resolve())):
                    return f"Error: Path '{file_path_str}' attempts to access a location outside the allowed directory."
                
                # Use the safe, absolute path with forward slashes for the command
                safe_file_path = str(full_path).replace('\\', '/')
                processed_parts.extend([part, safe_file_path])
                i += 2  # Skip the next part as we've already processed it
            else:
                processed_parts.append(part)
                i += 1
                
        # Rebuild and execute the command
        processed_command = ' '.join(processed_parts)
        try:
            return self.kubectl.execute(processed_command)
        except ValueError as e:
            return f"Error: {e}"
