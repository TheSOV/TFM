from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
from src.crewai.devops_flow.crews.devops_crew.outputs import outputs

@CrewBase
class GatherInformationCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/init_flow_tasks.yaml'

    @task
    def gather_information(self) -> Task:
        return Task(
            config=self.tasks_config['gather_information'], # type: ignore[index]
        )
    
    @task
    def research_project(self) -> Task:
        return Task(
            config=self.tasks_config['research_project'], # type: ignore[index]
        )
    
    @task
    def create_advanced_plan(self) -> Task:
        return Task(
            config=self.tasks_config['create_advanced_plan'], # type: ignore[index]
        )

    @task
    def create_basic_plan(self) -> Task:
        return Task(
            config=self.tasks_config['create_basic_plan'], # type: ignore[index]
            json_output=outputs.ImagesNames
        )
    
    