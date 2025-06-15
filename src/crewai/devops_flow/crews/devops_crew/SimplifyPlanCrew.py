from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew

@CrewBase
class SimplifyPlanCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/create_basic_plan.yaml'

    @task
    def create_basic_plan(self) -> Task:
        return Task(
            config=self.tasks_config['create_basic_plan'], # type: ignore[index]
        )
    
    