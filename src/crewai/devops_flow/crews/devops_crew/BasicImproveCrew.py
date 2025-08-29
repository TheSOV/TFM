from crewai import Crew, Task, Process
from crewai.project import CrewBase, task, crew
from src.crewai.devops_flow.crews.devops_crew.BaseCrew import BaseCrew
from src.services_registry import services
from src.crewai.devops_flow.blackboard.utils.Record import Record
from src.crewai.devops_flow.crews.devops_crew.guardrails.guardrails import validate_min_output_length_for_long_text
import src.crewai.devops_flow.crews.devops_crew.outputs.outputs as outputs
from crewai import LLMGuardrail, LLM
import os

@CrewBase   
class BasicImproveCrew(BaseCrew):
    """Description of your crew"""    
    tasks_config = 'tasks/basic_improve_tasks.yaml'

    @task
    def analyse_manifest_issue(self) -> Task:
        return Task(
            config=self.tasks_config['analyse_manifest_issue'], # type: ignore[index]
            output_json=outputs.Solutions,
            guardrail=LLMGuardrail("Verify that the proposed changes, in the changes field, of each solution, specifically addressing, and only addressing the problems described in the issues field, or related to them. Take in count that the changes proposed are only to to fix and make corrections in the Yaml files, so any problem that requires any action out of modifying the Yaml files, should not be taked into account.", llm=LLM(model=os.getenv("GUARDRAIL_MODEL")))
        )

    @task
    def apply_manifest_fix(self) -> Task:
        return Task(
            config=self.tasks_config['apply_manifest_fix'], # type: ignore[index]
        )

    @task
    def verify_solution(self) -> Task:
        return Task(
            config=self.tasks_config['verify_solution'], # type: ignore[index]
        )

    @task
    def log_manifest_fix(self) -> Task:
        return Task(
            config=self.tasks_config['log_manifest_fix'], # type: ignore[index]
            output_json=Record
        )