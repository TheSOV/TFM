from src.services_registry.services import get, init_services
from dotenv import load_dotenv
load_dotenv(override=True)

init_services()

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
    
    # tool = container.config_validator_tool()
    # result = tool.run(
    #     file_path="nginx-prod.yaml",
    #     file_type="kubernetes",
    #     enable_security_scan=True,
    #     skip_checks=[]
    # )
    # pprint(result)

    # read_tool = container.file_read_tool()
    # result = read_tool.run(file_path="nginx-prod.yaml")
    # pprint(result)

    validation_tool = get("config_validator")
    result = validation_tool._run(
        file_path="nginx-prod.yaml",
        file_type="kubernetes",
        enable_security_scan=True,
        skip_checks=[]
    )
    pprint(result)
