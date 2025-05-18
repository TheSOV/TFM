from src.crewai.tools.config_validator import ConfigValidatorTool
from src.crewai.tools.utils.checkov_validator import run_checkov_scan
from src.crewai.tools.utils.docker_validator import validate_docker_compose
from src.crewai.tools.utils.kubernetes_validator import validate_kubernetes_manifest
from src.crewai.tools.utils.yaml_validator import validate_yaml_file

from src.containers import Container

container = Container()
container.wire(modules=["src.crewai.tools.utils"])

from pprint import pprint


if __name__ == "__main__":
    # result = validate_yaml_file("temp/production_nginx_mysql.yaml")
    # pprint(result)

    # result = validate_kubernetes_manifest("temp/production_nginx_mysql.yaml")
    # pprint(result)

    # result = validate_docker_compose("temp/docker-compose.yml")
    # pprint(result)

    # result = run_checkov_scan("temp/production_nginx_mysql.yaml")
    # pprint(result)

    # tool = ConfigValidatorTool(base_dir="temp")
    # result = tool.run(
    #     file_path="production_nginx_mysql.yaml",
    #     file_type="kubernetes",
    #     enable_security_scan=True,
    #     skip_checks=[]
    # )
    # pprint(result)
    
    tool = container.config_validator_tool()
    result = tool.run(
        file_path="nginx-prod.yaml",
        file_type="kubernetes",
        enable_security_scan=True,
        skip_checks=[]
    )
    pprint(result)

