from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
from src.crewai.devops_flow.crews.devops_crew.outputs.outputs import Issues
from src.crewai.devops_flow.blackboard.utils.Record import Record
from src.crewai.devops_flow.crews.devops_crew.guardrails.guardrails import validate_min_output_length_for_long_text
from crewai import LLMGuardrail, LLM
import os

@CrewBase
class TestCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/test_tasks.yaml'

    @task
    def popeye_scan(self) -> Task:
        return Task(
            config=self.tasks_config['popeye_scan'], # type: ignore[index]
            guardrail=validate_min_output_length_for_long_text
        )

    @task
    def kubectl_status_check(self) -> Task:
        return Task(
            config=self.tasks_config['kubectl_status_check'], # type: ignore[index]
            guardrail=validate_min_output_length_for_long_text
        )

    @task
    def aggregate_cluster_issues(self) -> Task:
        return Task(
            config=self.tasks_config['aggregate_cluster_issues'], # type: ignore[index]
            output_json=Issues
        )

    @task
    def classify_cluster_issues(self) -> Task:
        return Task(
            config=self.tasks_config['classify_cluster_issues'], # type: ignore[index]
            output_json=Issues
        )
    
    @task
    def log_cluster_issues(self) -> Task:
        return Task(
            config=self.tasks_config['log_cluster_issues'], # type: ignore[index]
            output_json=Record
        )
    