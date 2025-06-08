from dotenv import load_dotenv
load_dotenv(override=True)

from src.crewai.devops_flow.MainFlow import MainFlow

main_flow = MainFlow()
main_flow.state.task = "create a nginx deployment"
main_flow.kickoff()

print(main_flow.state)