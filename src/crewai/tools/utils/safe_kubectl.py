# safe_kubectl.py
import shlex
import subprocess
from pathlib import Path
from typing import List, Set, Optional

class SafeKubectl:
    """
    A safe wrapper around kubectl that enforces security policies.
    
    Args:
        kubectl_path: Path to the kubectl binary
        allowed_verbs: Set of allowed kubectl verbs
        safe_namespaces: Set of allowed namespaces
        denied_namespaces: Set of denied namespaces
        deny_flags: Set of denied command-line flags
    """
    
    def __init__(
        self,
        kubectl_path: str = "/usr/bin/kubectl",
        allowed_verbs: Optional[Set[str]] = None,
        safe_namespaces: Optional[Set[str]] = None,
        denied_namespaces: Optional[Set[str]] = None,
        deny_flags: Optional[Set[str]] = None
    ) -> None:
        self.kubectl = Path(kubectl_path)
        self.allowed_verbs = allowed_verbs or {
            "get", "describe", "logs", "apply", "diff", "delete",
            "create", "patch", "exec", "cp", "rollout", "scale", "version"
        }
        # If safe_namespaces is None, it means all namespaces are allowed (except denied ones)
        self.safe_namespaces = safe_namespaces
        # If denied_namespaces is None, it means no namespaces are denied
        self.denied_namespaces = denied_namespaces or set()
        
        # Convert empty strings to None for safe_namespaces to match environment variable behavior
        if self.safe_namespaces is not None and not isinstance(self.safe_namespaces, set):
            self.safe_namespaces = set()
        self.deny_flags = deny_flags or {
            "--raw", "--kubeconfig", "--context", "-ojsonpath", "--output"
        }
    
    def _reject(self, msg: str) -> None:
        """Raise a ValueError with an error message."""
        raise ValueError(f"[safe-kubectl] BLOCKED: {msg}")
    
    def _parse(self, cmd: str) -> List[str]:
        """Parse and validate the command string."""
        bad = {";", "&", "|", "`", "$(", ">", "<"}
        if any(c in cmd for c in bad):
            self._reject("shell metacharacters detected")
        return shlex.split(cmd)
    
    def _validate(self, tokens: List[str]) -> None:
        """Validate the parsed command tokens against security policies."""
        if not tokens or tokens[0] != "kubectl":
            self._reject("command must start with 'kubectl'")
        
        tokens[0] = str(self.kubectl)  # replace with trusted path
        
        # Get the first non-flag token as the verb
        verb = next((t for t in tokens[1:] if not t.startswith("-")), None)
        if verb not in self.allowed_verbs:
            self._reject(f"verb '{verb}' not allowed")
        
        # Check for denied flags
        for flag in self.deny_flags:
            if flag in tokens:
                self._reject(f"flag '{flag}' blocked")
        
        # Check namespace restrictions
        self._validate_namespace(tokens, "-n")
        self._validate_namespace(tokens, "--namespace")
    
    def _validate_namespace(self, tokens: List[str], flag: str) -> None:
        # Check if namespace is allowed if specified
        if "-n" in tokens or "--namespace" in tokens:
            try:
                namespace_idx = tokens.index("-n") if "-n" in tokens else tokens.index("--namespace")
                namespace = tokens[namespace_idx + 1]
                
                # Check if namespace is explicitly denied
                if namespace in self.denied_namespaces:
                    self._reject(f"access to namespace '{namespace}' is explicitly denied")
                    
                # Check if safe namespaces is not None (empty set means allow all except denied)
                if self.safe_namespaces is not None and namespace not in self.safe_namespaces:
                    self._reject(f"namespace '{namespace}' is not in the allowed list")
                    
            except (IndexError, ValueError):
                self._reject("invalid namespace specification")
    
    def execute(self, command: str) -> str:
        """
        Execute a kubectl command with security validations.
        
        Args:
            command: The full kubectl command string
            
        Returns:
            str: Command output with exit code, stdout, and stderr
        """
        tokens = self._parse(command)
        self._validate(tokens)
        
        try:
            proc = subprocess.run(
                tokens,
                text=True,
                capture_output=True,
                shell=False,
                check=False
            )
            return (
                f"exit_code: {proc.returncode}\n"
                f"stdout:\n{proc.stdout.rstrip()}\n"
                f"stderr:\n{proc.stderr.rstrip()}"
            )
        except Exception as e:
            return f"error: {str(e)}"