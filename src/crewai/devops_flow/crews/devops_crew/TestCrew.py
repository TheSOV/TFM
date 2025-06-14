from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
from src.crewai.devops_flow.crews.devops_crew.outputs.outputs import Issues
from src.crewai.devops_flow.blackboard.utils.Record import Record

@CrewBase
class TestCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/test_tasks.yaml'

    @task
    def popeye_scan(self) -> Task:
        return Task(
            config=self.tasks_config['popeye_scan'], # type: ignore[index]
        )

    @task
    def kubectl_status_check(self) -> Task:
        return Task(
            config=self.tasks_config['kubectl_status_check'], # type: ignore[index]
        )

    @task
    def aggregate_cluster_issues(self) -> Task:
        return Task(
            config=self.tasks_config['aggregate_cluster_issues'], # type: ignore[index]
        )

    @task
    def issues_to_json(self) -> Task:
        return Task(
            config=self.tasks_config['issues_to_json'], # type: ignore[index]
            output_json=Issues
        )
    
    @task
    def log_cluster_issues(self) -> Task:
        return Task(
            config=self.tasks_config['log_cluster_issues'], # type: ignore[index]
            output_json=Record
        )
    