from kubernetes import client, config, utils
from kubernetes.client.rest import ApiException
from pathlib import Path
import os
import subprocess
import logging


class ClusterManager:
    def __init__(self, base_dir: str = "temp", dir_path: str = ""):
        # Load kubeconfig from default location
        config.load_kube_config()
        self.k8s_client = client.ApiClient()
        self.base_dir = base_dir
        self.dir_path = dir_path

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
        full_path = Path(self.base_dir) / self.dir_path / file_path
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
            full_path = Path(self.base_dir) / self.dir_path / file_path
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

    def create_namespace(self, namespace: str) -> None:
        """Create a Kubernetes namespace if it does not already exist.

        Parameters
        ----------
        namespace : str
            Name of the namespace to create.
        """
        if not namespace:
            raise ValueError("Namespace name must be a non-empty string")

        v1 = client.CoreV1Api(self.k8s_client)

        try:
            v1.read_namespace(name=namespace)
            # Namespace exists – nothing to do
            return
        except ApiException as exc:
            if exc.status != 404:
                # Unexpected error
                raise

        # Namespace does not exist – create it
        body = client.V1Namespace(
            metadata=client.V1ObjectMeta(name=namespace)
        )
        v1.create_namespace(body=body)

    def create_namespaces(self, namespaces: list[str]) -> None:
        """Create multiple namespaces if missing.

        Parameters
        ----------
        namespaces : list[str]
            List of namespace names to ensure exist.
        """
        for ns in namespaces:
            try:
                self.create_namespace(ns)
            except Exception as exc:
                raise exc

    def create_from_directory(self) -> str:
        """
        Recursively apply all YAML files in a directory and its subdirectories using kubectl CLI.

        Args:
            dir_path: Relative path to the directory from TEMP_FILES_DIR
        Returns:
            str: The stdout from kubectl apply
        Raises:
            RuntimeError: If kubectl apply fails
        """
        base_dir = Path(self.base_dir)
        try:
            result = subprocess.run(
                ["kubectl", "apply", "-R", "-f", str(base_dir / self.dir_path)],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"kubectl apply failed: {e.stderr}")

    def delete_from_directory(self) -> str:
        """
        Recursively delete all YAML-defined resources in a directory and its subdirectories using kubectl CLI.

        Args:
            dir_path: Relative path to the directory from TEMP_FILES_DIR
        Returns:
            str: The stdout from kubectl delete
        Raises:
            RuntimeError: If kubectl delete fails
        """
        base_dir = Path(self.base_dir)
        try:
            result = subprocess.run(
                ["kubectl", "delete", "-R", "-f", str(base_dir / self.dir_path)],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"kubectl delete failed: {e.stderr}")