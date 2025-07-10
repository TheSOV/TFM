import os
import logging
import time
import traceback
import asyncio
import datetime
import threading
from typing import Optional

import src.services_registry.services as services

from src.crewai.devops_flow.blackboard.utils.Issue import SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW

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
from src.crewai.devops_flow.crews.devops_crew.PerResourceResearchCrew import PerResourceResearchCrew

from src.crewai.devops_flow.crews.devops_crew.event_listener.event_listener import DevopsEventListener

from src.k8s.cluster import ClusterManager
from src.k8s.kind import KindManager

from pprint import pprint
import pickle
import asyncio
import json
import traceback
import yaml

import mlflow
import datetime

mlflow.set_tracking_uri("http://127.0.0.1:9500") # TODO: Make this configurable

services.init_services()

logger = logging.getLogger(__name__)

# Debug: Print logger information
print(f"DevopsFlow logger name: {logger.name}")
print(f"DevopsFlow logger level: {logger.level}")
print(f"DevopsFlow logger effective level: {logger.getEffectiveLevel()}")
print(f"DevopsFlow logger handlers: {logger.handlers}")
print(f"Root logger handlers: {logging.getLogger().handlers}")

class DevopsFlow:
    def __init__(self, user_request: str, path: str = "project", file_path: str = "manifests.yaml"):
        self.path = path
        self.base_dir = os.getenv("TEMP_FILES_DIR", "temp")
        self.filename = file_path

        self.blackboard = services.get("blackboard")
        self.event_listener = DevopsEventListener(self.blackboard)
        self.blackboard.reset()  # Reset to a clean state
        self.blackboard.project.user_request = user_request

        # Get the kill signal event from the service registry
        self.kill_signal: threading.Event = services.get("kill_signal_event")
        self.user_input_wait_event: threading.Event = services.get("user_input_wait_event")
        self.user_input_received_event: threading.Event = services.get("user_input_received_event")
        
        # Test log to verify logging is working
        logger.info(f"DevopsFlow initialized with user_request: {user_request[:50]}...")
        self.kill_signal.clear() # Clear at the start of a new flow instance

        k8s_version = os.getenv("K8S_VERSION", "v1.29.0")
        self.kind_manager = KindManager(k8s_version=k8s_version)
        self.cluster_manager = None

        services.init_services_with_path(self.path, file_path)

    async def _wait_for_user_input(self, step_name: str) -> Optional[str]:
        """
        Pauses the flow if in 'assisted' mode, waiting for user feedback.

        Args:
            step_name: The name of the step that is waiting for input.

        Returns:
            The user's feedback message if provided, otherwise None.
        """
        if self.blackboard.interaction.mode == "automated":
            return None

        logger.info(f"Pausing for user input before step: {step_name}")
        self.blackboard.interaction.status = f"waiting_for_input:{step_name}"
        self.user_input_wait_event.set()
        self.user_input_received_event.clear()

        try:
            while not self.user_input_received_event.is_set():
                if self.kill_signal.is_set():
                    logger.info("Kill signal detected while waiting for user input.")
                    self.blackboard.interaction.status = "running"
                    self.user_input_wait_event.clear()
                    return None
                await asyncio.sleep(1)  # Non-blocking wait

            # Immediately update state to prevent race conditions
            self.blackboard.interaction.is_waiting_for_input = False
            self.blackboard.interaction.step_name = ""
            self.blackboard.interaction.status = "running"

            user_feedback = self.blackboard.interaction.user_feedback
            self.blackboard.interaction.user_feedback = ""  # Clear feedback after reading

            self.user_input_received_event.clear()

            logger.info("User input received, resuming.")
            return user_feedback
        finally:
            # Ensure the received event is always cleared to prevent stale state
            self.user_input_received_event.clear()

    # TODO move this to parent
    def clear_temp_files(self):
        """
        Delete all content from the temp folder specified in TEMP_FILES_DIR environment variable.
        Creates the directory if it doesn't exist.
        """
        temp_dir = os.path.join(os.getenv("TEMP_FILES_DIR", "temp"), self.path)
        
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

        Returns:
            list[str]: Absolute paths of the deleted files or directories.
        """
        deleted: list[str] = []
        base_dir = os.path.abspath(os.getenv("TEMP_FILES_DIR", "temp"))
        full_path = os.path.abspath(os.path.join(base_dir, self.path))
        
        if not os.path.exists(full_path):
            logger.warning(f"Workspace directory does not exist: {full_path}")
            return deleted

        # Build set of paths referenced in the project's file_path
        project_file = os.path.join(full_path, self.filename)
        manifest_paths = {os.path.abspath(project_file).lower()}
        
        # Track directories to potentially remove if empty
        dirs_to_check = set()

        # Remove untracked files
        for root, dirs, files in os.walk(full_path, topdown=False):
            # Process files
            for fname in files:
                file_path = os.path.normpath(os.path.join(root, fname))
                
                # Skip if in .git directory or is a .gitkeep file
                # Normalize path for consistent checking and see if '.git' is a component
                normalized_check_path = file_path.replace(os.sep, '/')
                if f'/.git/' in f'/{normalized_check_path}/' or fname.lower() == '.gitkeep':
                    logger.debug(f"Preserving Git-related file: {file_path}")
                    continue
                    
                # Skip other Git housekeeping files
                git_housekeeping = {'.gitignore', '.gitattributes', '.gitmodules'}
                if fname.lower() in git_housekeeping:
                    logger.debug(f"Preserving Git file: {file_path}")
                    continue

                # Check if file is tracked (case-insensitive comparison)
                if file_path.lower() not in manifest_paths:
                    try:
                        os.remove(file_path)
                        deleted.append(file_path)
                        logger.debug(f"Removed untracked file: {file_path}")
                        # Add parent directory to check if it becomes empty
                        dirs_to_check.add(os.path.dirname(file_path))
                    except OSError as e:
                        logger.error(f"Failed to remove {file_path}: {e}")

            # Process directories (in bottom-up order)
            for dir_name in dirs:
                dir_path = os.path.normpath(os.path.join(root, dir_name))
                
                # Always preserve .git directories
                # Normalize path for consistent checking and see if '.git' is a component
                normalized_check_path = dir_path.replace(os.sep, '/')
                if f'/.git/' in f'/{normalized_check_path}/':
                    logger.debug(f"Preserving Git directory: {dir_path}")
                    continue

                # Check if directory is empty and not in manifest paths
                try:
                    contents = os.listdir(dir_path)
                    # Check if directory is empty or only contains .gitkeep
                    is_empty = (not contents or 
                              (len(contents) == 1 and contents[0].lower() == '.gitkeep'))
                    
                    if is_empty and dir_path.lower() not in manifest_paths:
                        try:
                            # Remove .gitkeep if it exists
                            gitkeep_path = os.path.join(dir_path, '.gitkeep')
                            if os.path.exists(gitkeep_path):
                                os.remove(gitkeep_path)
                                logger.debug(f"Removed .gitkeep from directory: {dir_path}")
                            
                            os.rmdir(dir_path)
                            deleted.append(dir_path)
                            logger.debug(f"Removed empty directory: {dir_path}")
                        except OSError as e:
                            # Directory might not be empty due to concurrent operations
                            logger.debug(f"Could not remove directory {dir_path}: {e}")
                except OSError as e:
                    logger.error(f"Error accessing directory {dir_path}: {e}")
        
        logger.info(f"Removed {len(deleted)} untracked items")
        return deleted


    def apply_k8s_config(self):   
        self.cluster_manager.create_from_directory()
    
    def delete_k8s_config(self):
        try:
            self.cluster_manager.delete_from_directory()
        except Exception as ex:
            logger.error(f"Deleting Manifest: {str(ex)}")


    @retry_with_feedback(max_attempts=3, delay=10)
    async def initial_research(self, feedback: Optional[str] = None):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting initial_research.")
            return
        logger.info("Initial research")

        advanced_crew = GatherInformationCrew(path=self.path).crew()

        inputs = {
                "blackboard": self.blackboard.export_blackboard(),
                "feedback": feedback,
            }
        logger.info(f"Kicking off 'initial_research' crew with feedback: '{feedback}'")
        advanced_results = await advanced_crew.kickoff_async(inputs=inputs)

        self.blackboard.project.advanced_plan = advanced_results.raw   


    @retry_with_feedback(max_attempts=3, delay=10)
    async def define_project_structure(self, feedback: Optional[str] = None):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting define_project_structure.")
            return
        logger.info("Define project structure")

        crew = DefinePreliminartStructureCrew(path=self.path).crew()

        results = await crew.kickoff_async(
            inputs={
                "blackboard": self.blackboard.export_blackboard(),
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

        crew = ImageNameExtractionCrew(path=self.path).crew()

        results = await crew.kickoff_async(
            inputs={
                "blackboard": self.blackboard.export_blackboard(),
                "feedback": feedback,
            }
        )

        crews = []

        # Process each image in parallel
        for image_name in results.json_dict['images']:
            crew = ImageInformationCrew(path=self.path).crew()
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
    async def first_approach(self, manifests: list[Manifest], feedback: Optional[str] = None):
        """
        Create the first version of the manifests
        """
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting first_approach.")
            return None

        logger.info("First approach")
       
        manifests_dump = [manifest.model_dump() for manifest in manifests]

        inputs = {
                "manifests": manifests_dump,
                "blackboard": self.blackboard.export_blackboard(show_advanced_plan=False),
                "feedback": feedback,
            }
        logger.info(f"Kicking off 'first_approach' crew with feedback: '{feedback}'")
        results = await FirstApproachCrew(path=self.path).crew().kickoff_async(inputs=inputs)

        temp_dir = os.getenv("TEMP_FILES_DIR", "temp")
        relative_path = os.path.normpath(self.filename)
        abs_file_path = os.path.abspath(os.path.join(temp_dir, self.path, relative_path))
        
        if not os.path.isfile(abs_file_path):
            logger.warning(f"Manifest file at {abs_file_path} does not exist on disk.")
            raise FileNotFoundError(f"You forgot to create the {self.filename}. Try again and ensure that this time the file is created with the appropriate content. Use the yaml_write_{self.path} tool to create it, with the tool call Action: action_name Action Input: .....")

        return results


    @retry_with_feedback(max_attempts=3, delay=10)
    async def per_resource_research(self, feedback: Optional[str] = None):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting per_resource_research.")
            return

        resources = [manifest.model_dump() for manifest in self.blackboard.manifests]

        result = await PerResourceResearchCrew(path=self.path).crew().kickoff_async(
            inputs={
                "blackboard": self.blackboard.export_blackboard(),
                "feedback": feedback,
                "resources": resources,
            }
        )

        self.blackboard.manifests = [Manifest(**manifest) for manifest in result.json_dict['manifests']]

    def _ensure_namespaces_exist(self):
        """
        Ensures that all namespaces referenced in the current manifest file exist in the cluster.
        It parses the manifest, extracts all unique namespace identifiers, and then
        instructs the cluster manager to create them. This is crucial for preventing
        'namespace not found' errors during dry-runs or applications.
        """
        ### start of ensure namespace creation ###
        logger.info("Ensuring all namespaces from manifest file exist...")
        temp_dir = os.getenv("TEMP_FILES_DIR", "temp")
        manifest_path = os.path.join(temp_dir, self.path, self.filename)
        namespaces_to_create = set()

        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r') as f:
                    documents = yaml.safe_load_all(f)
                    for doc in documents:
                        if not doc or not isinstance(doc, dict):
                            continue
                        # Add namespace from the resource's metadata
                        if 'namespace' in doc.get('metadata', {}):
                            namespaces_to_create.add(doc['metadata']['namespace'])
                        # Add namespace from the Namespace resource's name
                        if doc.get('kind') == 'Namespace' and 'name' in doc.get('metadata', {}):
                            namespaces_to_create.add(doc['metadata']['name'])
            except Exception as e:
                logger.error(f"Could not parse {manifest_path} to extract namespaces: {e}")

        # Fallback to blackboard if parsing fails or yields no namespaces
        if not namespaces_to_create:
            logger.warning("No namespaces found in manifest file or file could not be read. Falling back to blackboard. The following namespaces will be created: " + str(self.blackboard.general_info.namespaces))
            namespaces_to_create.update(self.blackboard.general_info.namespaces)

        if namespaces_to_create:
            logger.info(f"Creating namespaces: {list(namespaces_to_create)}")
            self.cluster_manager.create_namespaces(list(namespaces_to_create))
        else:
            logger.info("No namespaces to create.")

        ### end of ensure namespace creation ###

    @retry_with_feedback(max_attempts=3, delay=10)
    async def test_cluster(self, feedback: Optional[str] = None):
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

        self._ensure_namespaces_exist()

        logger.info("Applying manifests")

        try:            
            self.apply_k8s_config()
        except Exception as ex:
            self.delete_k8s_config()

            error = str(ex).replace(self.base_dir, "").replace(self.path, "").replace("\\\\\\", "")

            logger.error(f"\n\nError applying the manifests: {error}\n\n")

            issue = Issue(
                issue="Error applying the manifests",
                severity=SEVERITY_HIGH,
                problem_description=error + "\n\n Ignore any warnings about namespace, focus on the fatal errors, and other warnings.",
                possible_manifest_file_path="see the description of the issue",
                observations="Apply failed",
            )

            self.blackboard.issues = [issue]
            return

        logger.info("Waiting up to 10 seconds before testing cluster, checking for kill signal...")
        # Wait up to 10 s, checking for kill-signal every 0.1 s
        for _ in range(100):
            if self.kill_signal.is_set():
                logger.info("Kill signal detected during wait in test_cluster. Aborting.")
                return
            await asyncio.sleep(0.1)
        logger.info("Testing cluster")

        crew = TestCrew(path=self.path).crew()

        logger.info("Testing cluster - kickoff_async")
        try:
            results = await crew.kickoff_async(
                inputs={
                    "blackboard": self.blackboard.export_blackboard(show_advanced_plan=False, show_records=False, show_high_issues=False, show_medium_issues=False, show_low_issues=False),
                    "feedback": feedback,
                }
            )

            logger.info("Testing cluster - kickoff_async - results task 4")
            issues = results.tasks_output[3].json_dict['issues']

            logger.info("Testing cluster - kickoff_async - results task 5")
            record = results.tasks_output[4].json_dict
        except asyncio.CancelledError as e:
            logger.warning(f"TestCrew kickoff was cancelled: {e}")
            raise # Re-raise for the retry decorator
        except Exception as e:
            logger.exception("An unexpected error occurred during TestCrew kickoff")
            raise

        for issue in issues:
            if 'created_at' in issue:
                issue.pop('created_at')

        logger.info("Testing cluster - kickoff_async - Update blackboard Issues and Records")
        self.blackboard.issues = [Issue(**issue) for issue in issues]

        logger.info("Testing cluster - kickoff_async - Update blackboard Record")
        self.blackboard.records.append(Record(**record))

        logger.info("Testing cluster - kickoff_async - Delete k8s config")
        try:
            self.delete_k8s_config()
        except Exception as ex:
            logger.error(f"Error deleting manifest: {str(ex)}")


    @retry_with_feedback(max_attempts=3, delay=10)
    async def basic_improve(self, issues: list[Issue], feedback: Optional[str] = None):   
        
        issues = [issue.model_dump() for issue in issues]

        result = await BasicImproveCrew(path=self.path).crew().kickoff_async(
                    inputs={
                        "blackboard": self.blackboard.export_blackboard(show_advanced_plan=False, show_manifests=True),
                        "feedback": feedback,
                        "issues": issues,
                    }
                )

        json_record = result.json_dict
        if 'created_at' in json_record:
            json_record.pop('created_at')
        self.blackboard.records.append(Record(**json_record))


    @retry_with_feedback(max_attempts=3, delay=10)
    async def low_importance_improve(self, issues: list[Issue], feedback: Optional[str] = None):   
        
        issues = [issue.model_dump() for issue in issues]

        result = await BasicImproveCrew(path=self.path).crew().kickoff_async(
                    inputs={
                        "blackboard": self.blackboard.export_blackboard(show_advanced_plan=False, show_manifests=True),
                        "feedback": feedback,
                        "issues": issues,
                    }
                )

        json_record = result.json_dict
        if 'created_at' in json_record:
            json_record.pop('created_at')
        self.blackboard.records.append(Record(**json_record))
      

    ############################################
    ##
    ## Flows
    ##
    ############################################

    async def initial_research_flow(self):
        """
        Execute the initial research flow with approval/rejection feedback loop.
        
        This flow will:
        1. Perform initial research
        2. Present results to user
        3. Allow user to approve or reject with feedback
        4. Retry with feedback if rejected
        5. Continue when approved or max retries reached
        """
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting initial_research_flow.")
            return
            
        logger.info("Starting initial research flow")
        attempt_count = 0
        
        while True:
            attempt_count += 1
            logger.info(f"Starting initial research attempt {attempt_count}")
            
            # Perform initial research with any previous feedback
            await self.initial_research(feedback=feedback if 'feedback' in locals() else None)
            
            # Present results and wait for user approval
            feedback = await self._wait_for_user_input("initial_research_review")
            logger.info(f"Received feedback for initial research: {feedback}")
            
            # Check if user approved or provided feedback for retry
            if feedback and feedback.lower().strip() == 'approve':
                logger.info("Initial research approved by user")
                break
                
            logger.info("User requested changes, retrying initial research with feedback")
            
        logger.info("Initial research flow completed")


    async def define_project_structure_flow(self):
        """
        Execute the project structure definition flow with approval/rejection feedback loop.
        
        This flow will:
        1. Define the initial project structure
        2. Present results to user
        3. Allow user to approve or reject with feedback
        4. Retry with feedback if rejected
        5. Continue when approved or max retries reached
        """
        self.blackboard.phase = "Defining Project Structure"
        logger.info("Starting project structure definition flow...")
        
        attempt_count = 0
        feedback = None
        
        while True:
            attempt_count += 1
            logger.info(f"Starting project structure definition attempt {attempt_count}...")
            
            # Save current state in case we need to retry
            original_manifests = self.blackboard.manifests.copy()
            
            try:
                # Perform project structure definition with any previous feedback
                await self.define_project_structure(feedback=feedback)
                
                # Present results and wait for user approval
                feedback = await self._wait_for_user_input("project_structure_review")
                logger.info(f"Received feedback for project structure: {feedback}")
                
                # Check if user approved or provided feedback for retry
                if feedback and feedback.lower().strip() == 'approve':
                    logger.info("Project structure approved by user")
                    break
                    
                logger.info("User requested changes, retrying project structure definition with feedback")
                
            except Exception as e:
                logger.error(f"Error during project structure definition: {str(e)}")
                # Restore original manifests on error
                self.blackboard.manifests = original_manifests
                logger.info("Restored original manifests after error")
                await asyncio.sleep(1)  # Small delay before retry
            
        logger.info("Project structure definition flow completed")

    async def get_images_flow(self):
        """
        Execute the image retrieval flow with approval/rejection feedback loop.
        
        This flow will:
        1. Retrieve image information
        2. Present results to user
        3. Allow user to approve or reject with feedback
        4. Retry with feedback if rejected
        5. Continue when approved or max retries reached
        """
        self.blackboard.phase = "Retrieving Image Information"
        logger.info("Starting image retrieval flow...")
        
        attempt_count = 0
        feedback = None
        
        while True:
            attempt_count += 1
            logger.info(f"Starting image retrieval attempt {attempt_count}...")
            
            # Save current state in case we need to retry
            original_images = self.blackboard.images.copy()
            
            try:
                # Perform image retrieval with any previous feedback
                await self.get_images(feedback=feedback)
                
                # Present results and wait for user approval
                feedback = await self._wait_for_user_input("image_retrieval_review")
                logger.info(f"Received feedback for image retrieval: {feedback}")
                
                # Check if user approved or provided feedback for retry
                if feedback and feedback.lower().strip() == 'approve':
                    logger.info("Image retrieval approved by user")
                    break
                    
                logger.info("User requested changes, retrying image retrieval with feedback")
                
            except Exception as e:
                logger.error(f"Error during image retrieval: {str(e)}")
                # Restore original images on error
                self.blackboard.images = original_images
                logger.info("Restored original images after error")
                await asyncio.sleep(1)  # Small delay before retry
            
        logger.info("Image retrieval flow completed")

    async def second_research_flow(self):
        self.blackboard.phase = "Defining Project Structure and Getting Images"
        
        # Run both flows in parallel
        await self.define_project_structure_flow()
        
        await self.get_images_flow()

    async def per_resource_research_flow(self):
        """
        Execute the per-resource research flow with approval/rejection feedback loop.
        
        This flow will:
        1. Perform research for all resources at once
        2. Present results to user
        3. Allow user to approve or reject with feedback
        4. Retry with feedback if rejected
        5. Continue when approved or max retries reached
        """
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting per_resource_research_flow.")
            return
            
        self.blackboard.phase = "Per Resource Research"
        logger.info("Starting per-resource research flow")
        
        attempt_count = 0
        feedback = None
        
        while True:
            attempt_count += 1
            # Store the current state of manifests to revert if needed
            original_manifests = self.blackboard.manifests.copy()
            
            try:
                logger.info(f"Starting per-resource research (attempt {attempt_count})")
                
                # Perform research for all resources with any previous feedback
                await self.per_resource_research(feedback=feedback)
                
                # Present results and wait for user approval
                feedback = await self._wait_for_user_input("per_resource_research_review")
                logger.info(f"Received feedback for per-resource research: {feedback}")
                
                # Check if user approved or provided feedback for retry
                if feedback and feedback.lower().strip() == 'approve':
                    logger.info("Per-resource research approved by user")
                    break
                    
                logger.info("User requested changes, retrying with feedback")
                
            except Exception as e:
                logger.error(f"Error during per-resource research: {str(e)}")
                # Restore original manifests on error
                self.blackboard.manifests = original_manifests
                logger.info("Restored original manifests after error")
                await asyncio.sleep(1)  # Small delay before retry
            
        logger.info("Per-resource research flow completed")

    async def prepare_environment_flow(self): 

        self.clear_temp_files()

        # Ensure the version-control repository exists in TEMP_FILES_DIR so that
        # subsequent tools can safely add/commit files.

        # fv = services.get(f"file_versioning_{self.path}")  # singleton instance
        # fv._ensure_repo()  # pylint: disable=protected-access

        self.kind_manager.recreate_cluster()
        self.cluster_manager = ClusterManager(base_dir=os.getenv("TEMP_FILES_DIR", "temp")) # TODO: This should be a service
        
        logger.info("Creating namespaces: " + str(self.blackboard.general_info.namespaces))
        self.cluster_manager.create_namespaces(self.blackboard.general_info.namespaces)


    async def first_approach_flow(self):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected at start of first_approach_flow. Aborting.")
            return

        logger.info("First approach flow")
        feedback = await self._wait_for_user_input("first_approach")
        logger.info(f"User feedback received for first_approach: '{feedback}'")
        logger.info("Passing user feedback to first_approach")
        result = await self.first_approach(manifests=self.blackboard.manifests, feedback=feedback) 

        logger.info("first_approach completed. Logging feedback for verification")
        logger.info(f"Feedback passed to first_approach: '{feedback}'")

        json_record = result.json_dict
        if 'created_at' in json_record:
            json_record.pop('created_at')
        self.blackboard.records.append(Record(**json_record))   

    async def basic_test_and_improve_flow(self):
        try:
            for iteration in range(10):
                self.blackboard.iterations += 1

                if self.kill_signal.is_set():
                    logger.info(f"Kill signal detected in basic_test_and_improve_flow loop, iteration {iteration}. Aborting.")
                    return  # Exit the flow method

                self.blackboard.phase = "Testing"
                logger.info(f"Starting testing iteration {iteration + 1}...")
                await self.test_cluster()
                logger.info(f"Testing iteration {iteration + 1} completed.")

                try:
                    issues = self.blackboard.issues
                    high_issues = [issue for issue in issues if issue.severity == SEVERITY_HIGH]
                    medium_issues = [issue for issue in issues if issue.severity == SEVERITY_MEDIUM]
                    low_issues = [issue for issue in issues if issue.severity == SEVERITY_LOW]
                except Exception as e:
                    self.blackboard.phase = "Error while processing issues"
                    logger.error(f"Error getting issues: {str(e)}")
                    continue

                if high_issues:
                    self.blackboard.phase = "Improving High Severity Issues"
                    logger.info(f"Found {len(high_issues)} high-severity issues. Starting improvement phase...")
                    self._ensure_namespaces_exist()
                    feedback = await self._wait_for_user_input(f"improve_high_severity_issues_{self.blackboard.iterations}")
                    logger.info(f"User feedback received for improve_high_severity_issues: '{feedback}'")
                    await self.basic_improve(high_issues, feedback=feedback)
                    logger.info("Improvement phase for high-severity issues completed.")
                elif medium_issues:
                    self.blackboard.phase = "Improving Medium and Low Severity Issues"
                    issues_to_fix = medium_issues + low_issues
                    logger.info(f"Found {len(medium_issues)} medium-severity and {len(low_issues)} low-severity issues. Starting improvement phase...")
                    self._ensure_namespaces_exist()
                    feedback = await self._wait_for_user_input(f"improve_medium_low_severity_issues_{self.blackboard.iterations}")
                    logger.info(f"User feedback received for improve_medium_low_severity_issues: '{feedback}'")
                    await self.low_importance_improve(issues_to_fix, feedback=feedback)
                    logger.info("Improvement phase for medium and low-severity issues completed.")
                else:
                    logger.info("No high or medium-severity issues found. Exiting test and improve flow.")
                    break

        except Exception as e:
            logger.error(f"An unexpected error occurred in basic_test_and_improve_flow: {e}")
            logger.error(traceback.format_exc())
            # Re-raising the exception can help in debugging if something else is catching it
            raise
            

    async def kickoff(self):
        try:
            loop = asyncio.get_running_loop()

            def loop_exception_handler(loop, context):
                logger.error(
                    "ASYNCIO EXCEPTION: %s", context.get("message"),
                    exc_info=context.get("exception")
                )

            loop.set_exception_handler(loop_exception_handler)

            logger.info("Starting DevopsFlow kickoff in 10 seconds...")
            await asyncio.sleep(10)

            unique_time_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            mlflow.set_experiment(f"devops_flow_{unique_time_id}")
            mlflow.crewai.autolog()

            # Flow begings here                

            if self.kill_signal.is_set():
                logger.info("Kill signal detected at the very start of kickoff. Aborting.")
                return
            
            logger.info("Starting DevopsFlow kickoff...")
            # Clear signal at the beginning of a full kickoff, in case it was set from a previous aborted run and not cleared by API
            self.blackboard.phase = "Initial Research"
            await self.initial_research_flow()

            if self.kill_signal.is_set():
                logger.info("Kill signal detected after initial_research_flow. Aborting kickoff.")
                return

            await self.second_research_flow()

            if self.kill_signal.is_set():
                logger.info("Kill signal detected after second_research_flow. Aborting kickoff.")
                return

            await self.per_resource_research_flow()

            if self.kill_signal.is_set():
                logger.info("Kill signal detected after per_resource_research_flow. Aborting kickoff.")
                return

            ###################################
            #
            # Start of saving/loading blackboard
            #
            ###################################

            # with open("blackboard.pkl", "rb") as f:
            #     self.blackboard = pickle.load(f)
            #     services._cache["blackboard"] = self.blackboard

            with open("blackboard.pkl", "wb") as f:
                pickle.dump(self.blackboard, f)

            ###################################
            #
            # End of saving/loading blackboard
            #
            ###################################

            self.blackboard.phase = "Preparing Environment"
            await self.prepare_environment_flow()            

            if self.kill_signal.is_set(): # Check before starting async flow
                logger.info("Kill signal detected before first_approach_flow. Aborting kickoff.")
                return
            
            self.blackboard.phase = "First Code Approach"
            await self.first_approach_flow()

            if self.kill_signal.is_set(): # Check before starting test and improve flow
                logger.info("Kill signal detected before basic_test_and_improve_flow. Aborting kickoff.")
                return
            
            self.blackboard.phase = "Test and Improve"
            await self.basic_test_and_improve_flow()

            self.blackboard.phase = "Completed"
            logger.info("DevopsFlow kickoff completed.")

            logger.info(self.blackboard.model_dump())
        except asyncio.CancelledError as e:
            logger.warning("kickoff() was cancelled: %s", e, exc_info=True)
            raise  # let retry/outer layer see it
        except Exception as e:
            logger.exception("Error during kickoff")
            self.blackboard.phase = f"DevopsFlow failed: {e}"
        finally:
            # Ensure the kill signal is set on any exit, clean or error
            self.kill_signal.set()
            logger.info("DevopsFlow kickoff finished. Kill signal set.")