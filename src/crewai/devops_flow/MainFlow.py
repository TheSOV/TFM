import os
import logging

from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from typing import List
from pydantic import BaseModel, Field

from src.services_registry.services import init_services

from src.crewai.devops_flow.crews.devops_crew.devops_crew__correct_config import DevopsCrewCorrectConfig
from src.crewai.devops_flow.crews.devops_crew.devops_crew__initial_config import DevopsCrewInitialConfig
from src.crewai.devops_flow.crews.devops_crew.devops_crew__test_config import DevopsCrewTestConfig
from src.crewai.devops_flow.crews.devops_crew.devops_crew__initial_data_retrieval import DevopsCrewInitialDataRetrieval

from src.crewai.devops_flow.MaintState import MainState

from src.k8s.cluster import ClusterManager
from src.k8s.kind import KindManager

import opik
from opik.integrations.crewai import track_crewai

init_services()

opik.configure(use_local=False)
track_crewai(project_name="devops_flow")

logger = logging.getLogger(__name__)

class MainFlow:
    def __init__(self):
        self.state = MainState()
        self.kind_manager = KindManager()
        self.cluster_manager = None

    @task(cache_policy=NO_CACHE)
    def clear_temp_files(self):
        """
        Delete all content from the temp folder specified in TEMP_FILES_DIR environment variable.
        Creates the directory if it doesn't exist.
        """
        temp_dir = os.getenv("TEMP_FILES_DIR", "temp")
        
        # Create directory if it doesn't exist
        os.makedirs(temp_dir, exist_ok=True)
        
        # Remove all files and subdirectories
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    import shutil
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.error(f"Failed to delete {file_path}. Reason: {e}")
                raise
                
        logger.info(f"Successfully cleared temp directory: {os.path.abspath(temp_dir)}")
        

    @task(cache_policy=NO_CACHE)
    def reset_cluster(self):
        self.kind_manager.recreate_cluster()
        self.cluster_manager = ClusterManager(base_dir=os.getenv("TEMP_FILES_DIR", "temp"))

    @task(cache_policy=NO_CACHE)
    def retrieve_initial_data(self):
        logger.info("Retrieving initial data")        
        result = DevopsCrewInitialDataRetrieval().crew().kickoff(
            inputs={"state": self.state.model_dump()}
        )
        logger.info("Initial data retrieved", result.json_dict)
        self.state.images_data = result.json_dict

    @task(cache_policy=NO_CACHE)
    def generate_initial_config(self):
        logger.info("Generating initial config")        
        result = DevopsCrewInitialConfig().crew().kickoff(
            inputs={"state": self.state.model_dump()}
        )
        logger.info("Initial config generated", result.json_dict)
        self.state.base_information = result.json_dict

    @task(cache_policy=NO_CACHE)
    def apply_k8s_config(self):
        json_dict = self.state.model_dump()
        try:
            logger.info(f"Applying Kubernetes manifest from: {json_dict['base_information']['file_path']}")            
            self.cluster_manager.create_from_yaml(json_dict['base_information']['file_path'])  # Pass relative path
            self.state.apply_succeeded = True
            self.state.apply_result = "Kubernetes manifest applied successfully"
        except Exception as ex:
            logger.error(f"Error applying manifest: {str(ex)}")
            try:
                self.cluster_manager.delete_from_yaml(json_dict['base_information']['file_path'])  # Pass relative path
            except Exception as delete_ex:
                logger.error(f"Error during cleanup: {str(delete_ex)}")
            finally:
                self.state.apply_succeeded = False
                self.state.apply_result = f"Failed to apply Kubernetes manifest: {str(ex)}"
    
    @task(cache_policy=NO_CACHE)
    def delete_k8s_config(self):
        json_dict = self.state.model_dump()
        try:
            logger.info(f"Deleting Kubernetes manifest from: {json_dict['base_information']['file_path']}")            
            self.cluster_manager.delete_from_yaml(json_dict['base_information']['file_path'])  # Pass relative path
        except Exception as ex:
            logger.error(f"Error deleting manifest: {str(ex)}")

    @task(cache_policy=NO_CACHE)
    def correct_k8s_apply_errors(self):
        logger.info("Correcting Kubernetes config")
        result = DevopsCrewCorrectConfig().crew().kickoff(inputs={
                "state": self.state.model_dump()
            })
        logger.info("Kubernetes config corrected", result.json_dict)
        self.state.base_information = result.json_dict
    
    @task(cache_policy=NO_CACHE)
    def correct_k8s_test_errors(self):
        logger.info("Correcting Kubernetes config")
        result = DevopsCrewCorrectConfig().crew().kickoff(inputs={
                "state": self.state.model_dump()
            })
        logger.info("Kubernetes config corrected", result.json_dict)
        self.state.base_information = result.json_dict

    @task(cache_policy=NO_CACHE)
    def test_k8s_config(self):
        logger.info("Testing Kubernetes config")
        result = DevopsCrewTestConfig().crew().kickoff(inputs={
                "state": self.state.model_dump()
            })
        logger.info("Kubernetes config tested", result.json_dict)
        self.state.cluster_test_result = result.json_dict

    @flow(cache_result_in_memory=False, flow_run_name="devops_flow")
    def kickoff(self):
        self.clear_temp_files()
        self.reset_cluster()
        self.retrieve_initial_data()
        self.generate_initial_config()
        
        while not self.state.model_dump()["apply_succeeded"] or not self.state.model_dump()["cluster_test_result"]["cluster_working"]:

            self.apply_k8s_config()            
            if not self.state.model_dump()["apply_succeeded"]:
                self.delete_k8s_config()
                self.correct_k8s_apply_errors()
                continue

            self.test_k8s_config()            
            if not self.state.model_dump()["cluster_test_result"]["cluster_working"]:
                self.delete_k8s_config()
                self.correct_k8s_test_errors()
                continue
        
            break
        return self.state.model_dump()
