from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
from src.services_registry import services
from src.crewai.devops_flow.blackboard.utils.Record import Record
from src.crewai.devops_flow.crews.devops_crew.guardrails.guardrails import validate_min_output_length_for_long_text

@CrewBase   
class BasicImproveCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/basic_improve_tasks.yaml'

    @task
    def analyse_manifest_issue(self) -> Task:
        return Task(
            config=self.tasks_config['analyse_manifest_issue'], # type: ignore[index]
            tools=[
                services.get(f"file_read_{self.path}"),
                services.get(f"file_version_history_{self.path}"),
                services.get(f"file_version_diff_{self.path}"),
                services.get(f"config_validator_{self.path}"),
                ],
            guardrails=[validate_min_output_length_for_long_text]
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