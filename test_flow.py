from dotenv import load_dotenv
load_dotenv(override=True)

import mlflow
mlflow.set_tracking_uri("http://127.0.0.1:9500")
mlflow.set_experiment("devops_flow")
mlflow.crewai.autolog()

from src.crewai.devops_flow.DevopsFlow import MainFlow

main_flow = MainFlow()
main_flow.state.task = "create a nginx deployment"
main_flow.kickoff()

print(main_flow.state)