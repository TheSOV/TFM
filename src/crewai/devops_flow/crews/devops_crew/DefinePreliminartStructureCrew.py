from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
from src.crewai.devops_flow.crews.devops_crew.outputs import outputs
from src.crewai.devops_flow.crews.devops_crew.guardrails.guardrails import validate_min_output_length_for_long_text

@CrewBase
class DefinePreliminartStructureCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/define_project_structure_tasks.yaml'

    @task
    def define_project_structure(self) -> Task:
        return Task(
            config=self.tasks_config['preliminary_structure'], # type: ignore[index]
            guardrail=validate_min_output_length_for_long_text
        )

    @task
    def structured_preliminary_structure(self) -> Task:
        return Task(
            config=self.tasks_config['structured_preliminary_structure'], # type: ignore[index]
            output_json=outputs.Manifests
        )
 

    
    
    