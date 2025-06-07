from dotenv import load_dotenv
load_dotenv(override=True)

# import openlit
# openlit.init(otlp_endpoint="http://127.0.0.1:4318", disable_metrics=True)

import opik
opik.configure(use_local=False)
from opik.integrations.crewai import track_crewai
track_crewai(project_name="crewai-integration-demo")

from src.services_registry.services import init_services
init_services()

from src.crewai.devops_flow.crews.devops_crew.devops_crew__initial_config import DevopsCrewInitialConfig

result = DevopsCrewInitialConfig().crew().kickoff(inputs={"task": "create a nginx deployment"})
print(result.json_dict)
