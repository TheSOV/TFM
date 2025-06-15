from src.crewai.devops_flow.blackboard.utils.Image import Image

from dotenv import load_dotenv
load_dotenv(override=True)

import os

# Set the script's directory as the current working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

import mlflow
import datetime
unique_time_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
mlflow.set_tracking_uri("http://127.0.0.1:9500")
mlflow.set_experiment(f"devops_flow_{unique_time_id}")
mlflow.crewai.autolog()

import logging
logging.basicConfig(level=logging.INFO)

from src.crewai.devops_flow.DevopsFlow import DevopsFlow

from pprint import pprint

main_flow = DevopsFlow("i need an nginx server, for an low number of simultaneous users. It is an inner service for a small enterprise.")
main_flow.kickoff()



