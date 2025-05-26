from src.crewai.crews.devops_crew.devops_crew import DevopsCrew
from dotenv import load_dotenv


load_dotenv(override=True)

import warnings
from pydantic.warnings import PydanticDeprecatedSince211   # new in 2.11+

warnings.filterwarnings("ignore", category=PydanticDeprecatedSince211)


from src.services_registry.services import init_services

init_services()

import mlflow
mlflow.crewai.autolog()
# Optional: Set a tracking URI and an experiment name if you have a tracking server
mlflow.set_tracking_uri("http://localhost:5050")
mlflow.set_experiment("CrewAI")



crew = DevopsCrew().crew()
crew.kickoff()

# from src.crewai.crews.agentic_rag_crew.agentic_rag_crew import AgenticRagCrew

# from dotenv import load_dotenv

# load_dotenv(override=True)

# import warnings
# from pydantic.warnings import PydanticDeprecatedSince211   # new in 2.11+

# warnings.filterwarnings("ignore", category=PydanticDeprecatedSince211)

# from src.services_registry.services import init_services

# init_services()

# import weave

# weave.init(project_name="testing the agent")

# crew = AgenticRagCrew().crew()
# crew.kickoff(inputs={"query": "What is DevOps?"})
