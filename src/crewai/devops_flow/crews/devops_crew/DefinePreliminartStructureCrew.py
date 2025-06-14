from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
from src.crewai.devops_flow.crews.devops_crew.outputs import outputs

@CrewBase
class DefinePreliminartStructureCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/define_project_structure_tasks.yaml'

    @task
    def define_project_structure(self) -> Task:
        return Task(
            config=self.tasks_config['preliminary_structure'], # type: ignore[index]
        )

    @task
    def structured_preliminary_structure(self) -> Task:
        return Task(
            config=self.tasks_config['structured_preliminary_structure'], # type: ignore[index]
            output_json=outputs.Manifests
        )
 

    
    
    