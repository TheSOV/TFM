from src.crewai.tools.docker_tool import DockerImageAnalysisTool
from pprint import pprint

repo     = 'nginx'
tag      = 'alpine'

tool = DockerImageAnalysisTool()
pprint(tool._run(repo, tag))





