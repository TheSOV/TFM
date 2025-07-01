"""
Kind cluster management tool.

This module provides functionality to manage local Kubernetes clusters using Kind.
It can delete existing clusters and create new ones with a specified Kubernetes version.
"""
from typing import Optional, Tuple
import subprocess
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KindManager:
    """
    A class to manage Kind Kubernetes clusters.
    
    This class provides methods to delete existing clusters and create new ones
    with a specified Kubernetes version.
    """
    
    def __init__(self, k8s_version: Optional[str] = None):
        """
        Initialize the KindClusterManager.
        
        Args:
            k8s_version: Optional Kubernetes version to use. If not provided,
                       it will be loaded from the .env file.
        """
        self.k8s_version = k8s_version
        self.kind_image = f"kindest/node:{self.k8s_version}"
        logger.info(f"Initialized KindClusterManager with Kubernetes version: {self.k8s_version}")
    
    def delete_cluster(self, cluster_name: str = "kind") -> Tuple[bool, str]:
        """
        Delete a Kind cluster.
        
        Args:
            cluster_name: Name of the cluster to delete.
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            logger.info(f"Deleting Kind cluster: {cluster_name}")
            result = subprocess.run(
                ["kind", "delete", "cluster", "--name", cluster_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'  # Replace undecodable characters instead of raising an error
            )
            
            if result.returncode == 0:
                msg = f"Successfully deleted cluster: {cluster_name}"
                logger.info(msg)
                return True, msg
            else:
                if "not found" in result.stderr:
                    msg = f"Cluster {cluster_name} not found, nothing to delete"
                    logger.info(msg)
                    return True, msg
                else:
                    msg = f"Failed to delete cluster {cluster_name}: {result.stderr}"
                    logger.error(msg)
                    return False, msg
                    
        except FileNotFoundError:
            msg = "Kind CLI not found. Please install Kind and ensure it's in your PATH."
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Error deleting cluster {cluster_name}: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def create_cluster(self, cluster_name: str = "kind", config_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Create a new Kind cluster.
        
        Args:
            cluster_name: Name for the new cluster.
            config_path: Optional path to a Kind config file.
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if Kind is installed
            subprocess.run(
                ["kind", "--version"], 
                check=True, 
                capture_output=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # Build the command
            cmd = ["kind", "create", "cluster", "--name", cluster_name, "--image", self.kind_image]
            
            # Add config file if provided
            if config_path:
                if not os.path.exists(config_path):
                    return False, f"Config file not found: {config_path}"
                cmd.extend(["--config", config_path])
            
            logger.info(f"Creating Kind cluster: {cluster_name} with image {self.kind_image}")
            
            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'  # Replace undecodable characters instead of raising an error
            )
            
            if result.returncode == 0:
                msg = f"Successfully created cluster: {cluster_name}"
                logger.info(msg)
                return True, msg
            else:
                msg = f"Failed to create cluster {cluster_name}: {result.stderr}"
                logger.error(msg)
                return False, msg
                
        except subprocess.CalledProcessError as e:
            msg = f"Kind CLI error: {str(e)}"
            logger.error(msg)
            return False, msg
        except FileNotFoundError:
            msg = "Kind CLI not found. Please install Kind and ensure it's in your PATH."
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Error creating cluster {cluster_name}: {str(e)}"
            logger.error(msg)
            return False, msg
            
    def recreate_cluster(self, cluster_name: str = "kind", config_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Delete an existing Kind cluster and create a new one.
        
        Args:
            cluster_name: Name of the cluster to recreate.
            config_path: Optional path to a Kind config file for cluster creation.
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Delete existing cluster
        success, msg = self.delete_cluster(cluster_name)
        if not success and "not found" not in msg:
            return False, f"Failed to delete existing cluster: {msg}"
        
        # Create new cluster
        success, msg = self.create_cluster(cluster_name, config_path)
        if not success:
            return False, f"Failed to create new cluster: {msg}"
        
        return True, f"Successfully recreated cluster: {cluster_name} with Kubernetes {self.k8s_version}"

# Example usage
if __name__ == "__main__":
    # Example: Recreate a cluster with default settings
    success, message = recreate_cluster()
    print(f"Success: {success}")
    print(f"Message: {message}")
