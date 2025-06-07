from src.crewai.devops_flow.crews.devops_crew.base_crew import BaseCrew
from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, task, crew, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent

import src.crewai.devops_flow.crews.devops_crew.outputs.outputs as outputs
import src.crewai.devops_flow.crews.devops_crew.guardrails.guardrails as guardrails

@CrewBase
class DevopsCrewInitialConfig(BaseCrew):
    """Description of your crew"""

    # Paths to your YAML configuration files
    # To see an example agent and task defined in YAML, checkout the following:
    # - Task: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    # - Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    tasks_config = 'tasks/tasks__create_init_config.yaml'

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

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # Automatically collected by the @agent decorator
            tasks=self.tasks,    # Automatically collected by the @task decorator. 
            process=Process.sequential,
            verbose=True,
            memory=False
        )