from crewai import Agent, Task
from src.crewai.agents.yaml_coding_agent import YamlCodingAgent
import weave

from dotenv import load_dotenv
load_dotenv(override=True)

from src.containers import Container

# Initialize Weave with your project name
weave.init(project_name="testing the agent")

container = Container()
container.wire(modules=["src.crewai.agents.yaml_coding_agent"])

agent = YamlCodingAgent()

task = Task(
    description="Design a k8s config file, production level, for nginx server, with a SQL database. Ngixn should accessible for users in port 5010. For communication between the nginx and the database, use the port 5432. Make a Rag query to search for technical and code best practices for production level k8s config files, then design the config file.",
    expected_output="A k8s yaml file, with the proper configuration for the nginx and the database.",
    agent=agent
)
output = agent.execute_task(task=task)
print(output)