from src.crewai.devops_flow.crews.devops_crew.base_crew import BaseCrew
from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, task, crew, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent

import src.crewai.devops_flow.crews.devops_crew.outputs.outputs as outputs
import src.crewai.devops_flow.crews.devops_crew.guardrails.guardrails as guardrails

import src.services_registry.services as services

from os import getenv
from typing import List

@CrewBase
class DevopsCrew(BaseCrew):
    """Description of your crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # Paths to your YAML configuration files
    # To see an example agent and task defined in YAML, checkout the following:
    # - Task: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    # - Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    agents_config = 'agents/agents.yaml'
    tasks_config = 'tasks/tasks__create_init_config.yaml'

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
            verbose=True,
            tools=[
                services.get("file_create"),
                services.get("file_edit"),
                services.get("file_read"),
                services.get("directory_read"),
                services.get("config_validator"),
            ]
        )

    @agent
    def devops_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['devops_researcher'], # type: ignore[index]
            llm=getenv("AGENT_MAIN_MODEL"),
            function_calling_llm=getenv("AGENT_TOOL_CALL_MODEL"),
            verbose=True,
            tools=[
                services.get("rag"),
                services.get("selenium_scraper"),
                services.get("docker_manifest_tool"),
                services.get("docker_image_details_tool")
            ]
        )

    @agent
    def devops_tester(self) -> Agent:
        return Agent(
            config=self.agents_config['devops_tester'], # type: ignore[index]
            llm=getenv("AGENT_MAIN_MODEL"),
            function_calling_llm=getenv("AGENT_TOOL_CALL_MODEL"),
            verbose=True,
            tools=[
                services.get("kubectl"),
                services.get("file_read"),
                services.get("directory_read")
            ]
        )

    @task
    def research_k8s_config(self) -> Task:
        return Task(
            config=self.tasks_config['research_k8s_config'] # type: ignore[index]
        )
    
    @task
    def research_image_data(self) -> Task:
        return Task(
            config=self.tasks_config['research_image_data'] # type: ignore[index]
        )

    @task
    def create_k8s_config(self) -> Task:
        task = Task(
            config=self.tasks_config['create_k8s_config'], # type: ignore[index]
            output_json=outputs.CreateK8sConfigOutput,
            guardrail=guardrails.validate_create_k8s_config
        )
        return task

    @task
    def research_k8s_testing(self) -> Task:
        return Task(
            config=self.tasks_config['research_k8s_testing'] # type: ignore[index]
        )

    @task
    def test_k8_configuration(self) -> Task:
        return Task(
            config=self.tasks_config['test_k8_configuration'] # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # Automatically collected by the @agent decorator
            tasks=self.tasks,    # Automatically collected by the @task decorator. 
            process=Process.sequential,
            verbose=True,
            memory=False
        )