from dotenv import load_dotenv
load_dotenv(override=True)

from pprint import pprint

import mlflow
mlflow.set_tracking_uri("http://127.0.0.1:9500")
mlflow.set_experiment("devops_flow")
mlflow.crewai.autolog()

from src.crewai.devops_flow.crews.devops_crew.GatherInformationCrew import GatherInformationCrew

from src.services_registry.services import init_services, get
init_services()

blackboard = get("blackboard")
blackboard.project.user_request = "I need a nginx deployment with 3 replicas, each with 2 vCPUs and 4GB of RAM."

crew = GatherInformationCrew().crew()
result = crew.kickoff(
    inputs={
        "blackboard": blackboard.model_dump()
    }
)

print("\n\n\n")
pprint(blackboard.model_dump())


