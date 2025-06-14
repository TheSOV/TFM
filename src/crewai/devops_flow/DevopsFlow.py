import os
import logging
import time
import threading
from typing import Optional

import src.services_registry.services as services

from src.crewai.devops_flow.blackboard.utils.Issue import SEVERITY_HIGH

from src.retry_mechanism.retry import retry_with_feedback

from src.crewai.devops_flow.blackboard.utils.Record import Record
from src.crewai.devops_flow.blackboard.utils.Issue import Issue
from src.crewai.devops_flow.blackboard.utils.Manifest import Manifest
from src.crewai.devops_flow.blackboard.utils.Image import Image

from src.crewai.devops_flow.crews.devops_crew.GatherInformationCrew import GatherInformationCrew
from src.crewai.devops_flow.crews.devops_crew.DefinePreliminartStructureCrew import DefinePreliminartStructureCrew
from src.crewai.devops_flow.crews.devops_crew.FirstApproachCrew import FirstApproachCrew
from src.crewai.devops_flow.crews.devops_crew.ImageInformationCrew import ImageInformationCrew
from src.crewai.devops_flow.crews.devops_crew.ImageNameExtractionCrew import ImageNameExtractionCrew
from src.crewai.devops_flow.crews.devops_crew.TestCrew import TestCrew
from src.crewai.devops_flow.crews.devops_crew.BasicImproveCrew import BasicImproveCrew

from src.k8s.cluster import ClusterManager
from src.k8s.kind import KindManager

from pprint import pprint
import pickle
import asyncio
import json

import mlflow
import datetime

mlflow.set_tracking_uri("http://127.0.0.1:9500") # TODO: Make this configurable

services.init_services()

logger = logging.getLogger(__name__)

class DevopsFlow:
    def __init__(self, user_request: str):

        self.blackboard = services.get("blackboard")
        self.blackboard.reset()  # Reset to a clean state
        self.blackboard.project.user_request = user_request

        # Get the kill signal event from the service registry
        self.kill_signal: threading.Event = services.get("kill_signal_event")
        self.kill_signal.clear() # Clear at the start of a new flow instance


        self.kind_manager = KindManager()
        self.cluster_manager = None


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

    def delete_untracked_files(self) -> list[str]:
        """Delete files in a workspace directory that are not referenced by any manifest tracked on the blackboard.

        Args:
            No arguments: The method uses the ``TEMP_FILES_DIR`` environment variable (default ``"temp"``) as base directory.

        Returns:
            list[str]: Absolute paths of the deleted files or directories.
        """
        deleted: list[str] = []
        base_dir = os.getenv("TEMP_FILES_DIR", "temp")
        # Build set of paths referenced in manifests relative to base_dir
        manifest_paths = {
            os.path.normpath(os.path.join(base_dir, m.file_path)) for m in self.blackboard.manifests
        }
        logger.debug("Pruning files/directories in %s not present in blackboard", base_dir)
        # Remove untracked files
        for root, _, files in os.walk(base_dir):
            for fname in files:
                fpath = os.path.normpath(os.path.join(root, fname))
                if fpath not in manifest_paths:
                    try:
                        os.remove(fpath)
                        deleted.append(fpath)
                        logger.debug("Removed %s", fpath)
                    except Exception as exc:
                        logger.warning("Could not remove %s: %s", fpath, exc)

        # Build set of directories that must be kept (all ancestor dirs of manifest files)
        keep_dirs: set[str] = set()
        for mpath in manifest_paths:
            cur = os.path.dirname(mpath)
            while cur.startswith(base_dir):
                keep_dirs.add(os.path.normpath(cur))
                if cur == base_dir:
                    break
                cur = os.path.dirname(cur)

        # Walk directories bottom-up to remove empty ones not in keep_dirs
        for root, dirs, _ in os.walk(base_dir, topdown=False):
            for d in dirs:
                dir_path = os.path.normpath(os.path.join(root, d))
                if dir_path not in keep_dirs:
                    try:
                        os.rmdir(dir_path)
                        deleted.append(dir_path)
                        logger.debug("Removed empty dir %s", dir_path)
                    except OSError:
                        # Directory not empty or removal failed
                        pass
        return deleted

    def reset_cluster(self):
        self.kind_manager.recreate_cluster()
        self.cluster_manager = ClusterManager(base_dir=os.getenv("TEMP_FILES_DIR", "temp"))
        self.cluster_manager.create_namespaces(self.blackboard.project.namespaces)


    def apply_k8s_config(self):
        try:
            self.cluster_manager.create_from_directory()
            return True
        except Exception as ex:
            logger.error(f"Error applying manifest: {str(ex)}")
            return False

    
    def delete_k8s_config(self):
        try:
            self.cluster_manager.delete_from_directory()
        except Exception as ex:
            logger.error(f"Error deleting manifest: {str(ex)}")


    @retry_with_feedback(max_attempts=3, delay=0.2)
    def initial_research(self, feedback: Optional[str] = None):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting initial_research.")
            return
        logger.info("Initial research")

        crew = GatherInformationCrew().crew()

        results = crew.kickoff(
            inputs={
                "blackboard": self.blackboard.export_blackboard(),
                "feedback": feedback,
            }
        )

        self.blackboard.project.advanced_plan = results.tasks_output[2].raw
        self.blackboard.project.basic_plan = results.raw
    

    @retry_with_feedback(max_attempts=3, delay=0.2)
    def define_project_structure(self, feedback: Optional[str] = None):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting define_project_structure.")
            return
        logger.info("Define project structure")

        crew = DefinePreliminartStructureCrew().crew()

        results = crew.kickoff(
            inputs={
                "blackboard": self.blackboard.export_blackboard(hide_advanced_plan=False, hide_basic_plan=False),
                "feedback": feedback,
            }
        )

        self.blackboard.manifests = [Manifest(**manifest) for manifest in results.json_dict['manifests']]

        namespaces = set()
        for manifest in self.blackboard.manifests:
            namespaces.add(manifest.namespace)
        self.blackboard.general_info.namespaces = list(namespaces)

        if self.kill_signal.is_set():
            logger.info("Kill signal detected before deleting untracked files.")
            return

        deleted_files = self.delete_untracked_files()
        if deleted_files:
            deleted_files_str = "\n".join([f"- {f}" for f in deleted_files])
            record_content = f"The following files/directories were deleted as they are not part of any manifest:\n{deleted_files_str}"
            self.blackboard.records.append(Record(record=record_content, type="info", source="DevopsFlow"))
            logger.info(f"Added record for deleted untracked files: {deleted_files_str}")

    @retry_with_feedback(max_attempts=3, delay=0.2)
    def get_image_names(self, feedback: Optional[str] = None):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting get_image_names.")
            return

        crew = ImageNameExtractionCrew().crew()

        results = crew.kickoff(
            inputs={
                "blackboard": self.blackboard.export_blackboard(hide_advanced_plan=False, hide_basic_plan=False),
                "feedback": feedback,
            }
        )

        images = []

        for image_name in results.json_dict['images']:
            crew = ImageInformationCrew().crew()
            result = crew.kickoff(
                inputs={
                    "blackboard": self.blackboard.export_blackboard(),
                    "image_name": image_name,
                    "feedback": None,
                }
            )
            images.extend(result.json_dict["images"])

        print(images)

        self.blackboard.images = [Image(**image) for image in images]


    @retry_with_feedback(max_attempts=3, delay=0.2)
    async def first_approach(self, manifest: Manifest, feedback: Optional[str] = None):
        if self.kill_signal.is_set():
            logger.info(f"Kill signal detected. Aborting first_approach for manifest: {manifest.file_path}")
            # For async methods, ensure we return something awaitable if necessary, or handle cancellation.
            # Here, simple return should be fine as the caller (first_approach_flow) will handle it.
            return None # Or appropriate default/marker for cancellation
        """
        Create the first version of the manifests
        """
        logger.info("First approach")

        results = await FirstApproachCrew().crew().kickoff_async(
            inputs={
                "manifest": manifest.model_dump(),
                "blackboard": self.blackboard.export_blackboard(),
                "feedback": feedback,
            }
        )

        temp_dir = os.getenv("TEMP_FILES_DIR", "temp")

        abs_file_path = os.path.join(temp_dir, manifest.file_path)
        if not os.path.isfile(abs_file_path):
            logger.warning(f"Manifest file at {abs_file_path} does not exist on disk.")
            raise FileNotFoundError(f"You forgot to create the {abs_file_path}. Try again and ensure that this time the file is created with the appropriate content.")

        return results


    @retry_with_feedback(max_attempts=3, delay=0.2)
    def test_cluster(self, feedback: Optional[str] = None):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting test_cluster.")
            return

        logger.info("Applying manifests")
        try:
            self.apply_k8s_config()
        except Exception as ex:
            try:
                self.delete_k8s_config()
            except Exception as ex:
                logger.error(f"Error deleting manifest: {str(ex)}")

            self.cluster_manager.create_namespaces(self.blackboard.general_info.namespaces)

            logger.error(f"Error applying manifest: {str(ex)}")

            issue = Issue(
                issue="Error applying the manifests",
                severity=SEVERITY_HIGH,
                problem_description=str(ex),
                possible_manifest_file_path="see the description of the issue",
                observations="Apply failed",
            )
            self.blackboard.issues.append(issue)
            return

        logger.info("Waiting up to 10 seconds before testing cluster, checking for kill signal...")
        for _ in range(100): # Check every 0.1 seconds for 10 seconds
            if self.kill_signal.is_set():
                logger.info("Kill signal detected during wait in test_cluster. Aborting.")
                return
            time.sleep(0.1)
        logger.info("Testing cluster")

        crew = TestCrew().crew()

        results = crew.kickoff(
            inputs={
                "blackboard": self.blackboard.export_blackboard(),
                "feedback": feedback,
            }
        )

        issues = results.tasks_output[3].json_dict['issues']
        record = results.tasks_output[4].json_dict

        self.blackboard.issues = [Issue(**issue) for issue in issues]
        self.blackboard.records.extend([Record(**record)])

        try:
            self.delete_k8s_config()
        except Exception as ex:
            logger.error(f"Error deleting manifest: {str(ex)}")

        self.cluster_manager.create_namespaces(self.blackboard.general_info.namespaces)


    @retry_with_feedback(max_attempts=3, delay=0.2)
    async def basic_improve(self, issues_by_manifest: dict[str, list[Issue]], feedback: Optional[str] = None):   
        
        executions = []
        for key, value in issues_by_manifest.items():
            executions.append(
                BasicImproveCrew().crew().kickoff_async(
                    inputs={
                        "blackboard": self.blackboard.export_blackboard(),
                        "feedback": feedback,
                        "issues": [issue.model_dump() for issue in value],
                    }
                )
            )

        results = await asyncio.gather(*executions)

        for result in results:
            json_record = result.json_dict
            self.blackboard.records.append(Record(**json_record))
      

    ############################################
    ##
    ## Flows
    ##
    ############################################

    def initial_research_flow(self):
        if self.kill_signal.is_set(): # Adding checks to individual flow wrappers too for robustness
            logger.info("Kill signal detected at start of initial_research_flow. Aborting.")
            return
        logger.info("Initial research flow")
        self.initial_research()


    def define_project_structure_flow(self) -> None:
        if self.kill_signal.is_set():
            logger.info("Kill signal detected at start of define_project_structure_flow. Aborting.")
            return
        """
        Run the first approach flow and ensure manifest status is valid.
        """
        self.define_project_structure()
        self.get_image_names()


    def prepare_environment_flow(self):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected at start of prepare_environment_flow. Aborting.")
            return
        self.clear_temp_files()
        self.kind_manager.recreate_cluster()
        self.cluster_manager = ClusterManager(base_dir=os.getenv("TEMP_FILES_DIR", "temp"))
        self.cluster_manager.create_namespaces(self.blackboard.general_info.namespaces)


    async def first_approach_flow(self):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected at start of first_approach_flow. Aborting.")
            return
        executions = []

        logger.info("First approach flow")
        for manifest in self.blackboard.manifests:
            if self.kill_signal.is_set():
                logger.info("Kill signal detected in first_approach_flow loop. Aborting.")
                return # Exit the flow method
            execution = self.first_approach(manifest)
            executions.append(execution)

        results = await asyncio.gather(*executions)
        for result in results:
            json_record = result.json_dict
            self.blackboard.records.append(Record(**json_record))  
            

    def basic_test_and_improve_flow(self):
        for i in range(10):
            if self.kill_signal.is_set():
                logger.info(f"Kill signal detected in basic_test_and_improve_flow loop, iteration {i}. Aborting.")
                return # Exit the flow method            
            self.test_cluster()

            issues = self.blackboard.issues
            high_issues = [issue for issue in issues if issue.severity == SEVERITY_HIGH]
            
            # Group high severity issues by possible_manifest_file_path
            issues_by_manifest = {}
            for issue in high_issues:
                manifest_path = issue.possible_manifest_file_path
                if manifest_path not in issues_by_manifest:
                    issues_by_manifest[manifest_path] = []
                issues_by_manifest[manifest_path].append(issue)

            if len(high_issues) == 0:
                break

            asyncio.run(self.basic_improve(issues_by_manifest))
            self.blackboard.iterations += 1

    def kickoff(self):
        logger.info("Starting DevopsFlow kickoff in 10 seconds...")
        time.sleep(10)

        unique_time_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        mlflow.set_experiment(f"devops_flow_{unique_time_id}")
        mlflow.crewai.autolog()

        if self.kill_signal.is_set():
            logger.info("Kill signal detected at the very start of kickoff. Aborting.")
            return
        
        logger.info("Starting DevopsFlow kickoff...")
        # Clear signal at the beginning of a full kickoff, in case it was set from a previous aborted run and not cleared by API
        self.blackboard.phase = "Initial Research"
        self.initial_research_flow()

        if self.kill_signal.is_set():
            logger.info("Kill signal detected after initial_research_flow. Aborting kickoff.")
            return

        self.blackboard.phase = "Defining Project Structure"
        self.define_project_structure_flow()

        if self.kill_signal.is_set():
            logger.info("Kill signal detected after define_project_structure_flow. Aborting kickoff.")
            return

        self.blackboard.phase = "Preparing Environment"
        self.prepare_environment_flow()

        if self.kill_signal.is_set(): # Check before starting async flow
            logger.info("Kill signal detected before first_approach_flow. Aborting kickoff.")
            return

        self.blackboard.phase = "First Code Approach"
        asyncio.run(self.first_approach_flow())

        if self.kill_signal.is_set(): # Check before starting test and improve flow
            logger.info("Kill signal detected before basic_test_and_improve_flow. Aborting kickoff.")
            return

        self.blackboard.phase = "Testing and Improvement"
        self.basic_test_and_improve_flow()

        self.blackboard.phase = "Completed"
        logger.info("DevopsFlow kickoff completed.")