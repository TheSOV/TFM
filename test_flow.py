from src.crewai.devops_flow.blackboard.utils.Image import Image

from dotenv import load_dotenv
load_dotenv(override=True)



import mlflow
import datetime
unique_time_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
mlflow.set_tracking_uri("http://127.0.0.1:9500")
mlflow.set_experiment(f"devops_flow_{unique_time_id}")
mlflow.crewai.autolog()

import logging
logging.basicConfig(level=logging.INFO)

from src.crewai.devops_flow.DevopsFlow import MainFlow

from pprint import pprint

main_flow = MainFlow("i need an nginx server, for an low number of simultaneous users. It is an inner service for a small enterprise.")
main_flow.kickoff()



