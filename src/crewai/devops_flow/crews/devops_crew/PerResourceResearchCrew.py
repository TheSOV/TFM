from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
from src.crewai.devops_flow.crews.devops_crew.guardrails.guardrails import validate_min_output_length_for_long_text

@CrewBase
class PerResourceResearchCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/per_resource_research_tasks.yaml'

    @task
    def per_resource_research(self) -> Task:
        return Task(
            config=self.tasks_config['per_resource_research'], # type: ignore[index]
            guardrail=validate_min_output_length_for_long_text
        )

    
    