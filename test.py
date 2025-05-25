from src.crewai.crews.devops_crew.devops_crew import DevopsCrew
import weave
from dotenv import load_dotenv


load_dotenv(override=True)

import warnings
from pydantic.warnings import PydanticDeprecatedSince211   # new in 2.11+

warnings.filterwarnings("ignore", category=PydanticDeprecatedSince211)


from src.services_registry.services import init_services

init_services()
weave.init(project_name="testing the agent")

crew = DevopsCrew().crew()
crew.kickoff()
# from dotenv import load_dotenv
# load_dotenv(override=True)

# from src.services_registry.services import init_services, get

# init_services()

# rag = get("rag")
# result = rag._run(
#     query="what is the role of the kubelet in kubernetes?",
#     collection="kubernetes_code"
# )
# # print(result)




        
