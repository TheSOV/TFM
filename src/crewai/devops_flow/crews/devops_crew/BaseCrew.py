from typing import List

from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, task, crew, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent

import src.crewai.devops_flow.crews.devops_crew.outputs.outputs as outputs
import src.crewai.devops_flow.crews.devops_crew.guardrails.guardrails as guardrails

import src.services_registry.services as services
from src.crewai.devops_flow.blackboard.Blackboard import Blackboard
from os import getenv

import src.crewai.devops_flow.crews.devops_crew.knowledge.devops_engineer as devops_engineer_knowledge
import src.crewai.devops_flow.crews.devops_crew.knowledge.devops_researcher as devops_researcher_knowledge
import src.crewai.devops_flow.crews.devops_crew.knowledge.devops_tester as devops_tester_knowledge
import src.crewai.devops_flow.crews.devops_crew.knowledge.devops_crew as devops_crew_knowledge

from crewai import Agent, Crew
from crewai.knowledge.knowledge_config import KnowledgeConfig
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource

knowledge_config = KnowledgeConfig(
    results_limit=5,
    score_threshold=0.6
)

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
                # services.get("file_version_history"),
                # services.get("file_version_diff"),
                # services.get("file_version_restore"),
                services.get("config_validator"),
            ],
            knowledge_sources=[
                StringKnowledgeSource(content=devops_engineer_knowledge.content),
            ],
            knowledge_config=knowledge_config
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
                services.get("stackoverflow_search"),
                services.get("web_browser_tool"),
                services.get("docker_image_analysis_tool"),
                services.get("docker_search_images_tool")
            ],
            knowledge_sources=[
                StringKnowledgeSource(content=devops_researcher_knowledge.content),
            ],
            knowledge_config=knowledge_config
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
            ],
            knowledge_sources=[
                StringKnowledgeSource(content=devops_tester_knowledge.content),
            ],
            knowledge_config=knowledge_config
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # Automatically collected by the @agent decorator
            tasks=self.tasks,    # Automatically collected by the @task decorator. 
            process=Process.sequential,
            planning=True,
            verbose=True,
            memory=True,
            knowledge_sources=[
                StringKnowledgeSource(content=devops_crew_knowledge.content),
            ],
        )   

    
    