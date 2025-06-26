from typing import List

from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, task, crew, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent

import src.crewai.devops_flow.crews.devops_crew.outputs.outputs as outputs
import src.crewai.devops_flow.crews.devops_crew.guardrails.guardrails as guardrails

import src.services_registry.services as services

from os import getenv

@CrewBase
class BaseCrew:
    """Description of your crew"""
    def __init__(self, path: str):
        """Initialize the BaseCrew with the given path.
        
        Args:
            path (str): The base path for the DevOps flow operations.
        """
        super().__init__()
        self.path = path

    agents: List[BaseAgent]
    tasks: List[Task]
    
    # Paths to your YAML configuration files
    # To see an example agent and task defined in YAML, checkout the following:
    # - Task: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    # - Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    agents_config = 'agents/agents.yaml'
    # tasks_config = 'tasks/tasks.yaml'

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
    def devops_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['devops_engineer'], # type: ignore[index]
            llm=getenv("AGENT_MAIN_MODEL"),
            function_calling_llm=getenv("AGENT_TOOL_CALL_MODEL"),
            verbose=False,
            tools=[
                services.get(f"file_create_{self.path}"),
                services.get(f"file_edit_{self.path}"),
                services.get(f"file_read_{self.path}"),
                services.get(f"file_version_history_{self.path}"),
                services.get(f"file_version_diff_{self.path}"),
                services.get(f"file_version_restore_{self.path}"),
                services.get(f"config_validator_{self.path}"),
            ],
        )

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
                services.get(f"file_read_{self.path}"),
                services.get(f"file_version_history_{self.path}"),
                services.get(f"file_version_diff_{self.path}"),
            ],
        )

    @agent
    def devops_tester(self) -> Agent:
        return Agent(
            config=self.agents_config['devops_tester'], # type: ignore[index]
            llm=getenv("AGENT_MAIN_MODEL"),
            function_calling_llm=getenv("AGENT_TOOL_CALL_MODEL"),
            verbose=False,
            tools=[
                services.get(f"kubectl_{self.path}"),
                services.get(f"file_read_{self.path}"),
                services.get("popeye_scan"),
            ],
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

    
    