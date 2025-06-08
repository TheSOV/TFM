from src.crewai.devops_flow.crews.devops_crew.base_crew import BaseCrew
from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, task, crew, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent

import src.crewai.devops_flow.crews.devops_crew.outputs.outputs as outputs
import src.crewai.devops_flow.crews.devops_crew.guardrails.guardrails as guardrails

from typing import List

@CrewBase
class DevopsCrewTestConfig(BaseCrew):
    """Description of your crew"""

    # Paths to your YAML configuration files
    # To see an example agent and task defined in YAML, checkout the following:
    # - Task: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    # - Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    tasks_config = 'tasks/tasks__test_config.yaml'

    @task
    def test_k8_configuration_popeye(self) -> Task:
        return Task(
            config=self.tasks_config['test_k8_configuration_popeye'] # type: ignore[index]
        )

    @task
    def test_k8_configuration_kubectl(self) -> Task:
        return Task(
            config=self.tasks_config['test_k8_configuration_kubectl'] # type: ignore[index]
        )

    @task
    def test_k8_configuration_report(self) -> Task:
        return Task(
            config=self.tasks_config['test_k8_configuration_report'], # type: ignore[index]
            output_json=outputs.TestK8sConfigOutput,
            guardrail=guardrails.validate_test_k8s_config
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # Automatically collected by the @agent decorator
            tasks=self.tasks,    # Automatically collected by the @task decorator. 
            process=Process.sequential,
            verbose=False,
            memory=False
        )