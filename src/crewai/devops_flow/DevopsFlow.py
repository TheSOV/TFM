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
from src.crewai.devops_flow.crews.devops_crew.PerResourceResearchCrew import PerResourceResearchCrew

from src.crewai.devops_flow.crews.devops_crew.event_listener.event_listener import DevopsEventListener

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
    def __init__(self, user_request: str, path: str = "project"):
        self.path = path
        self.base_dir = os.getenv("TEMP_FILES_DIR", "temp")

        self.blackboard = services.get("blackboard")
        self.event_listener = DevopsEventListener(self.blackboard)
        self.blackboard.reset()  # Reset to a clean state
        self.blackboard.project.user_request = user_request

        # Get the kill signal event from the service registry
        self.kill_signal: threading.Event = services.get("kill_signal_event")
        self.kill_signal.clear() # Clear at the start of a new flow instance

        self.kind_manager = KindManager()
        self.cluster_manager = None

        services.init_services_with_path(self.path)

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

        # Build set of paths referenced in manifests
        manifest_paths = set()
        for m in self.blackboard.manifests:
            try:
                # Normalize and resolve the manifest path
                # Use the robust, consistent path normalization pattern
                relative_path = os.path.normpath(m.file_path).replace('\\', '/').lstrip('/')
                abs_manifest_path = os.path.abspath(os.path.join(full_path, relative_path))
                
                # Ensure the path is within our workspace for security
                if not abs_manifest_path.startswith(full_path):
                    logger.warning(f"Manifest path outside workspace: {abs_manifest_path}")
                    continue
                    
                manifest_paths.add(abs_manifest_path.lower())  # Case-insensitive comparison
                logger.debug(f"Tracking manifest path: {abs_manifest_path}")
            except Exception as e:
                logger.error(f"Error processing manifest path {m.file_path}: {e}")

        logger.info(f"Pruning untracked files in {full_path}")
        
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


    def reset_cluster(self):
        self.kind_manager.recreate_cluster() # TODO move this to parent
        self.cluster_manager = ClusterManager(base_dir=os.getenv("TEMP_FILES_DIR", "temp"), dir_path=self.path)
        
        logger.info(self.blackboard.model_dump())
        logger.info(self.blackboard.project.model_dump())
        
        self.cluster_manager.create_namespaces(self.blackboard.project.namespaces)


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

        advanced_results = await advanced_crew.kickoff_async(
            inputs={
                "blackboard": self.blackboard.export_blackboard(),
                "feedback": feedback,
            }
        )

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

        # Process each image sequentially
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

        results = await FirstApproachCrew(path=self.path).crew().kickoff_async(
            inputs={
                "manifest": manifest.model_dump(),
                "blackboard": self.blackboard.export_blackboard(show_advanced_plan=False),
                "feedback": feedback,
            }
        )

        temp_dir = os.getenv("TEMP_FILES_DIR", "temp")
        # Normalize path separators and handle leading slashes using the consistent pattern
        relative_path = os.path.normpath(manifest.file_path).replace('\\', '/').lstrip('/')
        abs_file_path = os.path.abspath(os.path.join(temp_dir, self.path, relative_path))
        
        logger.debug(f"Temporary directory: {temp_dir}")
        logger.debug(f"Project path: {self.path}")
        logger.debug(f"Manifest file path: {manifest.file_path}")
        logger.debug(f"Resolved absolute path: {abs_file_path}")
        
        if not os.path.isfile(abs_file_path):
            logger.warning(f"Manifest file at {abs_file_path} does not exist on disk.")
            raise FileNotFoundError(f"You forgot to create the {abs_file_path}. Try again and ensure that this time the file is created with the appropriate content. Use the file_create tool to create it, with the tool call Action: action_name Action Input: .....")

        return results


    @retry_with_feedback(max_attempts=3, delay=10)
    async def per_resource_research(self, feedback: Optional[str] = None):
        if self.kill_signal.is_set():
            logger.info("Kill signal detected. Aborting per_resource_research.")
            return
        
        logger.info("Per resource research")

        per_resource_research_crews = []
        
        for manifest in self.blackboard.manifests:
            crew = PerResourceResearchCrew(path=self.path).crew()
            per_resource_research_crews.append(
                crew.kickoff_async(
                    inputs={
                        "blackboard": self.blackboard.export_blackboard(),
                        "feedback": feedback,
                        "resource": manifest.model_dump(),
                    }
                )
            )

        # Wait for all crews to complete and get their results
        results = await asyncio.gather(*per_resource_research_crews)
       
        # Pair results with manifests by order and update descriptions
        if len(results) != len(self.blackboard.manifests):
            logger.warning(f"Mismatch in number of results ({len(results)}) and manifests ({len(self.blackboard.manifests)})")
            
        # Update each manifest's description with the corresponding result
        for i, (result, manifest) in enumerate(zip(results, self.blackboard.manifests)):
            if result is None:
                logger.warning(f"Skipping None result at index {i}")
                continue
                
            try:
                manifest.description = result.raw
                logger.info(f"Updated description for manifest: {manifest.file_path}")
            except Exception as e:
                logger.error(f"Failed to update manifest at index {i} (file: {manifest.file_path}): {str(e)}")


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

        logger.info("Applying manifests")
        
        self.cluster_manager.create_namespaces(self.blackboard.general_info.namespaces)

        try:            
            self.apply_k8s_config()
        except Exception as ex:
            self.delete_k8s_config()

            error = str(ex).replace(self.base_dir, "").replace(self.path, "").replace("\\\\\\", "")

            logger.error(f"\n\nError applying the manifests: {error}\n\n")

            issue = Issue(
                issue="Error applying the manifests",
                severity=SEVERITY_HIGH,
                problem_description=error + "\n\n Ignore any warnings, focus on the fatal errors",
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

        crew = TestCrew(path=self.path).crew()

        results = await crew.kickoff_async(
            inputs={
                "blackboard": self.blackboard.export_blackboard(show_advanced_plan=False, show_records=False, show_high_issues=False, show_medium_issues=False, show_low_issues=False),
                "feedback": feedback,
            }
        )

        issues = results.tasks_output[4].json_dict['issues']
        logger.info(10*"\n" + f"Issues: {issues}")

        record = results.tasks_output[5].json_dict
        logger.info(10*"\n" + f"Record: {record}")

        for issue in issues:
            if 'created_at' in issue:
                issue.pop('created_at')
        logger.info(10*"\n" + f"Issues after removing created_at: {issues}")

        if 'created_at' in record:
            record.pop('created_at')
        logger.info(10*"\n" + f"Record after removing created_at: {record}")

        self.blackboard.issues = [Issue(**issue) for issue in issues]
        self.blackboard.records.append(Record(**record))
        logger.info(10*"\n" + f"Blackboard: updated")

        try:
            self.delete_k8s_config()
        except Exception as ex:
            logger.error(f"Error deleting manifest: {str(ex)}")


    @retry_with_feedback(max_attempts=3, delay=10)
    async def basic_improve(self, issues_by_manifest: dict[str, list[Issue]], feedback: Optional[str] = None):   
        
        executions = []
        for key, value in issues_by_manifest.items():
            executions.append(
                BasicImproveCrew(path=self.path).crew().kickoff_async(
                    inputs={
                        "blackboard": self.blackboard.export_blackboard(show_advanced_plan=False, show_manifests=False),
                        "feedback": feedback,
                        "issues": [issue.model_dump() for issue in value],
                    }
                )
            )

        results = await asyncio.gather(*executions)

        for result in results:
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
        logger.info("Initial research flow")
        await self.initial_research()


    async def second_research_flow(self):
        self.blackboard.phase = "Defining Project Structure and Getting Images"
        
        project_structure_flow = self.define_project_structure()
        get_images_flow = self.get_images()

        await asyncio.gather(project_structure_flow, get_images_flow)

    async def per_resource_research_flow(self):
        self.blackboard.phase = "Per Resource Research"
        await self.per_resource_research()

    async def prepare_environment_flow(self): 

        self.clear_temp_files()

        # Ensure the version-control repository exists in TEMP_FILES_DIR so that
        # subsequent tools can safely add/commit files.

        fv = services.get(f"file_versioning_{self.path}")  # singleton instance
        fv._ensure_repo()  # pylint: disable=protected-access

        self.kind_manager.recreate_cluster()
        self.cluster_manager = ClusterManager(base_dir=os.getenv("TEMP_FILES_DIR", "temp")) # TODO: This should be a service
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
            if 'created_at' in json_record:
                json_record.pop('created_at')
            self.blackboard.records.append(Record(**json_record))
            

    async def basic_test_and_improve_flow(self):
        
        for i in range(10):
            self.blackboard.iterations += 1

            if self.kill_signal.is_set():
                logger.info(f"Kill signal detected in basic_test_and_improve_flow loop, iteration {i}. Aborting.")
                return # Exit the flow method    

            self.blackboard.phase = "Testing"
            await self.test_cluster()

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
            await self.basic_improve(issues_by_manifest)
            

    async def kickoff(self):
        try:
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

            self.blackboard.phase = "Preparing Environment"
            await self.prepare_environment_flow()

            if self.kill_signal.is_set(): # Check before starting async flow
                logger.info("Kill signal detected before first_approach_flow. Aborting kickoff.")
                return

            # with open("blackboard.pkl", "rb") as f:
            #     self.blackboard = pickle.load(f)
            #     services._cache["blackboard"] = self.blackboard
            #     pprint(self.blackboard)

            with open("blackboard.pkl", "wb") as f:
                pickle.dump(self.blackboard, f)

            self.blackboard.phase = "First Code Approach"
            await self.first_approach_flow()

            if self.kill_signal.is_set(): # Check before resetting cluster
                logger.info("Kill signal detected before resetting cluster. Aborting kickoff.")
                return
            
            self.blackboard.phase = "Resetting Cluster"
            self.reset_cluster()

            if self.kill_signal.is_set(): # Check before starting test and improve flow
                logger.info("Kill signal detected before basic_test_and_improve_flow. Aborting kickoff.")
                return
            
            self.blackboard.phase = "Basic Test and Improve"
            await self.basic_test_and_improve_flow()

            self.blackboard.phase = "Completed"
            logger.info("DevopsFlow kickoff completed.")

            logger.info(self.blackboard.model_dump())
        except Exception as e:
            logger.error(f"Error during kickoff: {str(e)}", exc_info=True)
            self.blackboard.phase = f"DevopsFlow failed {str(e)}"
        finally:
            self.kill_signal.set()
            