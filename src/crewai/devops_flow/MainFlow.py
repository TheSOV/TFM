import os

from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from typing import List

from src.crewai.devops_flow.crews.devops_crew.devops_crew__correct_config import DevopsCrewCorrectConfig
from src.crewai.devops_flow.crews.devops_crew.devops_crew__initial_config import DevopsCrewInitialConfig

from src.k8s.cluster import ClusterManager
from src.k8s.kind import KindManager

import opik
from opik.integrations.crewai import track_crewai
opik.configure(use_local=False)
track_crewai(project_name="crewai-integration-demo")

import logging
logger = logging.getLogger(__name__)

class MainState:
    task: str | None = None
    file_path: str | None = None
    known_issues: List[str] = []
    apply_succeeded: bool = False
    apply_result: str | None = None

class MainFlow:
    def __init__(self):
        self.state = MainState()
        self.kind_manager = KindManager()
        self.cluster_manager = None

    @task(cache_policy=NO_CACHE)
    def reset_cluster(self):
        self.kind_manager.recreate_cluster()
        self.cluster_manager = ClusterManager(base_dir=os.getenv("TEMP_FILES_DIR", "temp"))

    @task(cache_policy=NO_CACHE)
    def generate_initial_config(self):
        logger.info("Generating initial config")        
        result = DevopsCrewInitialConfig().crew().kickoff(inputs={"task": self.state.task})
        logger.info("Initial config generated", result.json_dict)
        self.state.file_path = result.json_dict["file_path"]
        self.state.known_issues = result.json_dict["non_solved_issues"]

    @task(cache_policy=NO_CACHE)
    def apply_k8s_config(self):
        try:
            logger.info(f"Applying Kubernetes manifest from: {self.state.file_path}")            
            self.cluster_manager.create_from_yaml(self.state.file_path)  # Pass relative path
            self.state.apply_succeeded = True
            self.state.apply_result = "Kubernetes manifest applied successfully"
        except Exception as ex:
            logger.error(f"Error applying manifest: {str(ex)}")
            try:
                self.cluster_manager.delete_from_yaml(self.state.file_path)  # Pass relative path
            except Exception as delete_ex:
                logger.error(f"Error during cleanup: {str(delete_ex)}")
            finally:
                self.state.apply_succeeded = False
                self.state.apply_result = f"Failed to apply Kubernetes manifest: {str(ex)}"

    @task(cache_policy=NO_CACHE)
    def correct_k8s_config(self):
        logger.info("Correcting Kubernetes config")
        result = DevopsCrewCorrectConfig().crew().kickoff(inputs={
                "task": self.state.task,
                "file_path": self.state.file_path,
                "apply_errors": self.state.apply_result,
                "known_issues": self.state.known_issues
            })
        logger.info("Kubernetes config corrected", result.json_dict)
        self.state.file_path = result.json_dict["file_path"]
        self.state.known_issues = result.json_dict["non_solved_issues"]

    @flow(cache_result_in_memory=False, flow_run_name="devops_flow")
    def kickoff(self):
        self.reset_cluster()
        self.generate_initial_config()
        while not self.state.apply_succeeded:
            self.apply_k8s_config()
            if self.state.apply_succeeded:
                break
            self.correct_k8s_config()
        return self.state
