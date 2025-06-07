from dotenv import load_dotenv
load_dotenv(override=True)

from src.services_registry.services import init_services
init_services()

from src.crewai.devops_flow.MainFlow import MainFlow

main_flow = MainFlow()
main_flow.kickoff()
print(main_flow.state)