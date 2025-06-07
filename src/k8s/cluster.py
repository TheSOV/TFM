from kubernetes import client, config, utils
from pathlib import Path
import os

class ClusterManager:
    def __init__(self, base_dir: str = "temp"):
        # Load kubeconfig from default location
        config.load_kube_config()
        self.k8s_client = client.ApiClient()
        self.base_dir = base_dir

    def create_from_yaml(self, file_path: str):
        """Create Kubernetes resources from a YAML file.
        
        Args:
            file_path: Relative path to the YAML file from TEMP_FILES_DIR
            
        Returns:
            The result from utils.create_from_yaml
            
        Raises:
            FileNotFoundError: If the YAML file doesn't exist
            RuntimeError: If there's an error applying the YAML
        """
        full_path = Path(self.base_dir) / file_path
        return utils.create_from_yaml(self.k8s_client, str(full_path), verbose=True)

    def delete_from_yaml(self, file_path: str) -> str:
        """Delete Kubernetes resources defined in the YAML file using kubectl CLI.
        
        Args:
            file_path: Relative path to the YAML file from TEMP_FILES_DIR
            
        Returns:
            str: The output from the kubectl command.
            
        Raises:
            RuntimeError: If the kubectl command fails.
        """
        import subprocess
        try:
            full_path = Path(self.base_dir) / file_path
            result = subprocess.run(
                ["kubectl", "delete", "-f", str(full_path)],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to delete resources: {e.stderr}"
            raise RuntimeError(error_msg) from e