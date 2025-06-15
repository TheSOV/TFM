import os
import logging
import time
import threading
from typing import Optional

import src.services_registry.services as services

from src.crewai.devops_flow.blackboard.utils.Issue import SEVERITY_HIGH

from src.retry_mechanism.retry import retry_with_feedback

from src.crewai.devops_flow.blackboard.Blackboard import Blackboard
from src.crewai.devops_flow.blackboard.utils.Image import Image
from src.crewai.devops_flow.blackboard.utils.Issue import Issue
from src.crewai.devops_flow.blackboard.utils.Manifest import Manifest
from src.crewai.devops_flow.blackboard.utils.Record import Record

from src.crewai.devops_flow.crews.devops_crew.GatherInformationCrew import GatherInformationCrew
from src.crewai.devops_flow.crews.devops_crew.DefinePreliminartStructureCrew import DefinePreliminartStructureCrew
from src.crewai.devops_flow.crews.devops_crew.FirstApproachCrew import FirstApproachCrew
from src.crewai.devops_flow.crews.devops_crew.ImageInformationCrew import ImageInformationCrew
from src.crewai.devops_flow.crews.devops_crew.ImageNameExtractionCrew import ImageNameExtractionCrew
from src.crewai.devops_flow.crews.devops_crew.TestCrew import TestCrew
from src.crewai.devops_flow.crews.devops_crew.BasicImproveCrew import BasicImproveCrew
from src.crewai.devops_flow.crews.devops_crew.SimplifyPlanCrew import SimplifyPlanCrew

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
                # Skip special Git housekeeping files (e.g., .gitkeep, .gitignore, .gitattributes)
                git_housekeeping = {'.gitkeep', '.gitignore', '.gitattributes'}
                if os.path.basename(fpath).lower() in git_housekeeping:
                    continue
                # Skip anything inside a hidden .git directory that might exist (defensive)
                if os.sep + '.git' + os.sep in fpath:
                    continue

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
                # Never delete Git metadata directories
                if os.path.basename(dir_path) == '.git' or os.sep + '.git' + os.sep in dir_path:
                    continue

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


    @retry_with_feedback(max_attempts=3, delay=10)
    def initial_research(self, feedback: Optional[str] = None):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting initial_research.")
            return
        logger.info("Initial research")

        advanced_crew = GatherInformationCrew().crew()

        advanced_results = advanced_crew.kickoff(
            inputs={
                "blackboard": self.blackboard.export_blackboard(hide_advanced_plan=False, hide_basic_plan=False),
                "feedback": feedback,
            }
        )

        self.blackboard.project.advanced_plan = advanced_results.raw

        basic_crew = SimplifyPlanCrew().crew()
        basic_results = basic_crew.kickoff(
            inputs={
                "blackboard": self.blackboard.export_blackboard(hide_advanced_plan=False, hide_basic_plan=False),
                "feedback": feedback,
            }
        )   
        self.blackboard.project.basic_plan = basic_results.raw
    

    @retry_with_feedback(max_attempts=3, delay=10)
    def define_project_structure(self, feedback: Optional[str] = None):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting define_project_structure.")
            return
        logger.info("Define project structure")

        crew = DefinePreliminartStructureCrew().crew()

        results = crew.kickoff(
            inputs={
                "blackboard": self.blackboard.export_blackboard(hide_advanced_plan=False, hide_basic_plan=True),
                "feedback": feedback,
            }
        )

        self.blackboard.manifests = [Manifest(**manifest) for manifest in results.json_dict['manifests']]

        namespaces = set()
        for manifest in self.blackboard.manifests:
            namespaces.add(manifest.namespace)

        # Filter out invalid namespace identifiers without mutating the set while iterating
        filtered_namespaces = [ns for ns in namespaces if ns.lower().strip() != "n/a"]
        self.blackboard.general_info.namespaces = filtered_namespaces


    @retry_with_feedback(max_attempts=3, delay=10)
    async def get_images(self, feedback: Optional[str] = None):

        crew = ImageNameExtractionCrew().crew()

        results = crew.kickoff(
            inputs={
                "blackboard": self.blackboard.export_blackboard(hide_advanced_plan=False, hide_basic_plan=False),
                "feedback": feedback,
            }
        )

        crews = []

        # Process each image sequentially
        for image_name in results.json_dict['images']:
            crew = ImageInformationCrew().crew()
            # Await the kickoff directly and process the result
            crews.append(crew.kickoff_async(
                inputs={
                    "blackboard": self.blackboard.export_blackboard(),
                    "image_name": image_name,
                    "feedback": None,
                }
            ))

        results = await asyncio.gather(*crews)
        images = []
        for result in results:
            images.append(result.json_dict)

        new_images = []
        for image_data in images:
            new_images.append(Image(**image_data))

        self.blackboard.images = new_images


    @retry_with_feedback(max_attempts=3, delay=10)
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


    @retry_with_feedback(max_attempts=3, delay=10)
    def test_cluster(self, feedback: Optional[str] = None):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting test_cluster.")
            return
        
        logger.info("Deleting untracked files")
        deleted_files = self.delete_untracked_files()
        if deleted_files:
            deleted_files_str = "\n".join([f"- {f}" for f in deleted_files])
            record_content = (
                "The following files/directories were deleted as they are not part of any manifest:\n"
                f"{deleted_files_str}"
            )
            self.blackboard.records.append(
                Record(
                    agent="devops_engineer",
                    task_name="delete_untracked_files",
                    task_description=record_content,
                )
            )
            logger.info(f"Added record for deleted untracked files: {deleted_files_str}")

        logger.info("Applying manifests")
        
        try:
            self.cluster_manager.create_namespaces(self.blackboard.general_info.namespaces)
            self.apply_k8s_config()
        except Exception as ex:
            try:
                self.delete_k8s_config()
            except Exception as ex:
                logger.error(f"Error deleting manifest: {str(ex)}")

            logger.error(f"Error applying manifest: {str(ex)}")

            issue = Issue(
                issue="Error applying the manifests",
                severity=SEVERITY_HIGH,
                problem_description=str(ex),
                possible_manifest_file_path="see the description of the issue",
                observations="Apply failed",
            )
            self.blackboard.issues = [issue]
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
                "blackboard": self.blackboard.export_blackboard(show_records=False, show_high_issues=False, show_medium_issues=False, show_low_issues=False),
                "feedback": feedback,
            }
        )

        issues = results.tasks_output[3].json_dict['issues']
        record = results.tasks_output[4].json_dict

        self.blackboard.issues = [Issue(**issue) for issue in issues]
        self.blackboard.records.append(Record(**record))

        try:
            self.delete_k8s_config()
        except Exception as ex:
            logger.error(f"Error deleting manifest: {str(ex)}")

        self.cluster_manager.create_namespaces(self.blackboard.general_info.namespaces)


    @retry_with_feedback(max_attempts=3, delay=10)
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
        logger.info("Initial research flow")
        self.initial_research()


    def define_project_structure_flow(self) -> None:
        """
        Run the first approach flow and ensure manifest status is valid.
        """
        self.define_project_structure()

    def get_images_flow(self):
        """
        Run the get images flow
        """
        asyncio.run(self.get_images())


    def prepare_environment_flow(self):

        self.clear_temp_files()

        # Ensure the version-control repository exists in TEMP_FILES_DIR so that
        # subsequent tools can safely add/commit files.

        fv = services.get("file_versioning")  # singleton instance
        fv._ensure_repo()  # pylint: disable=protected-access

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
            execution = self.first_approach(manifest)
            executions.append(execution)

        results = await asyncio.gather(*executions)
        for result in results:
            json_record = result.json_dict
            self.blackboard.records.append(Record(**json_record))
            

    def basic_test_and_improve_flow(self):
        
        for i in range(10):
            self.blackboard.iterations += 1

            if self.kill_signal.is_set():
                logger.info(f"Kill signal detected in basic_test_and_improve_flow loop, iteration {i}. Aborting.")
                return # Exit the flow method    

            self.blackboard.phase = "Testing"
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

            self.blackboard.phase = "Improving"
            asyncio.run(self.basic_improve(issues_by_manifest))
            

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

        self.blackboard.phase = "Getting Images"
        self.get_images_flow()

        if self.kill_signal.is_set():
            logger.info("Kill signal detected after get_images_flow. Aborting kickoff.")
            return

        with open("blackboard.pkl", "wb") as f:
            pickle.dump(self.blackboard, f)

        with open("blackboard.pkl", "rb") as f:
            self.blackboard = pickle.load(f)
            import src.services_registry.services as services
            services._cache["blackboard"] = self.blackboard

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
        
        self.basic_test_and_improve_flow()

        self.blackboard.phase = "Completed"
        logger.info("DevopsFlow kickoff completed.")

        logger.info(self.blackboard.model_dump())
        