from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
from src.services_registry import services
from src.crewai.devops_flow.blackboard.utils.Record import Record

@CrewBase
class BasicImproveCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/basic_improve_tasks.yaml'

    @task
    def analyse_manifest_issue(self) -> Task:
        return Task(
            config=self.tasks_config['analyse_manifest_issue'], # type: ignore[index]
            tools=[
                services.get("file_read"),
                services.get("file_version_history"),
                services.get("file_version_diff"),
                services.get("config_validator"),
                ]
        )

    @task
    def apply_manifest_fix(self) -> Task:
        return Task(
            config=self.tasks_config['apply_manifest_fix'], # type: ignore[index]
        )

    @task
    def log_manifest_fix(self) -> Task:
        return Task(
            config=self.tasks_config['log_manifest_fix'], # type: ignore[index]
            output_json=Record
        )