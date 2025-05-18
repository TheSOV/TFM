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
    description="""Design a k8s config file name nginx-prod.yaml, production level, for nginx server. Nginx should be accessible for users in port 5010 through an ingress. Follow the next steps: 
    1. Make a Rag query to search for definitions, best practices and code examples for production level k8s config files. 
    2. Design and write the config file
    3. Check it with config_validator_tool:
    4. If it is not valid, use Rag to search for information about the problems found and use the edit tool to fix the problems found and go to step 3.
    5. If it is valid, justify the choices made.
    """,
    expected_output="A k8s yaml file, with the proper configuration for the nginx and the database, and a response justifying the choices made.",
    agent=agent
)
output = agent.execute_task(task=task)
print(output)