# from crewai import Task
# from crewai.project import CrewBase, task
# from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
# import src.crewai.devops_flow.crews.devops_crew.outputs.outputs as outputs


# @CrewBase   
# class ConsultCrew(BaseCrew):
#     """Description of your crew"""    
#     tasks_config = 'tasks/consult_tasks.yaml'

#     @task
#     def consult(self) -> Task:
#         return Task(
#             config=self.tasks_config['consult'], # type: ignore[index]
#             output_json=outputs.Solutions,
#         )
from typing import List

from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, task, crew, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.knowledge.knowledge_config import KnowledgeConfig
import os

import src.services_registry.services as services

from os import getenv

crew_knowledge_base_path = os.path.join(os.getcwd(), 'knowledge', 'crew')
files = []

for file in os.listdir(crew_knowledge_base_path):
    files.append(os.path.join("crew", file))

crew_knowledge_source = TextFileKnowledgeSource(file_paths=files)
crew_knowledge_config = KnowledgeConfig(results_limit=5, score_threshold=0.5)


@CrewBase
class ConsultCrew:
    """Description of your crew"""
    def __init__(self):
        """Initialize the BaseCrew with the given path.
        
        Args:
            path (str): The base path for the DevOps flow operations.
        """
        super().__init__()

    agents: List[BaseAgent]
    tasks: List[Task]
    
    # Paths to your YAML configuration files
    # To see an example agent and task defined in YAML, checkout the following:
    # - Task: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    # - Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    agents_config = 'agents/agents.yaml'
    tasks_config = 'tasks/consult_tasks.yaml'

    @task
    def consult(self) -> Task:
        return Task(
            config=self.tasks_config['consult'], # type: ignore[index]
        )

    @before_kickoff
    def prepare_inputs(self, inputs):
        # Modify inputs before the crew starts
        # inputs['additional_data'] = "Some extra information"
        return inputs

    @after_kickoff
    def process_output(self, output):
        # Modify output after the crew finishes
        # output.raw += "\nProcessed after kickoff."
        return output

    @agent
    def devops_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['devops_researcher'], # type: ignore[index]
            llm=getenv("AGENT_MAIN_MODEL"),
            function_calling_llm=getenv("AGENT_TOOL_CALL_MODEL"),
            verbose=False,
            tools=[
                services.get("rag"),
                services.get("stackoverflow_search"),
                services.get("web_browser_tool"),
                services.get("docker_image_analysis_tool"),
                services.get("docker_search_images_tool"),
            ]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # Automatically collected by the @agent decorator
            tasks=self.tasks,    # Automatically collected by the @task decorator. 
            process=Process.sequential,
            planning=False,
            verbose=False,
            memory=False,
        )   

    
    