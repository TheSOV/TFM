from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
from src.crewai.devops_flow.crews.devops_crew.outputs import outputs

@CrewBase
class ImageInformationCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/image_information_tasks.yaml'

    @task
    def get_image_information(self) -> Task:
        return Task(
            config=self.tasks_config['get_image_information'], # type: ignore[index]
            output_json=outputs.Images
        )

    
    