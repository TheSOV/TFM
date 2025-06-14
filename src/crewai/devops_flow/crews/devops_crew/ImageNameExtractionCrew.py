from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
from src.crewai.devops_flow.crews.devops_crew.outputs import outputs

@CrewBase
class ImageNameExtractionCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/image_name_extraction_tasks.yaml'

    @task
    def get_image_names(self) -> Task:
        return Task(
            config=self.tasks_config['get_image_names'], # type: ignore[index]
            output_json=outputs.ImagesNames
        )

    
    