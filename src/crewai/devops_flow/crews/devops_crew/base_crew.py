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
            verbose=True,
            tools=[
                services.get("file_create"),
                services.get("file_edit"),
                services.get("file_read"),
                # services.get("directory_read"),
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
                services.get("docker_manifest_tool"),
                services.get("docker_image_details_tool"),
                services.get("docker_pullable_digest_tool")
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
                services.get("popeye_scan"),
                # services.get("directory_read")
            ]
        )