from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
from src.services_registry import services
from src.crewai.devops_flow.blackboard.utils.Record import Record
from src.crewai.devops_flow.crews.devops_crew.guardrails.guardrails import validate_min_output_length_for_long_text

@CrewBase
class FirstApproachCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/first_approach_tasks.yaml'

    @task
    def write_solution(self) -> Task:
        return Task(
            config=self.tasks_config['write_solution'], # type: ignore[index]
        )

    @task
    def verify_solution(self) -> Task:
        return Task(
            config=self.tasks_config['verify_solution'], # type: ignore[index]
        )

    @task
    def log_solution(self) -> Task:
        return Task(
            config=self.tasks_config['log_solution'], # type: ignore[index]
            tools=[],
            output_json=Record
        )