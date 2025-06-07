from src.services_registry.services import get, init_services
from src.crewai.tools.utils.k8s_dry_run import k8s_dry_run
from src.crewai.tools.utils.docker_dry_run import docker_dry_run
from dotenv import load_dotenv
load_dotenv(override=True)

init_services()

from pprint import pprint


if __name__ == "__main__":
    # result = get("rag")._run(
    #     query="what is the role of the kubelet in kubernetes?",
    #     collection="kubernetes_code"
    # )
    # pprint(result)

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

    # validation_tool = get("config_validator")
    # result = validation_tool._run(
    #     file_path="nginx-prod.yaml",
    #     file_type="kubernetes",
    #     enable_security_scan=True,
    #     skip_checks=[]
    # )
    # pprint(result)

    # result = k8s_dry_run("temp/nginx-prod.yaml")
    # pprint(result)

    # result = docker_dry_run("docker-compose.yml")
    # pprint(result)

    # docker_manifest_tool = get("docker_manifest_tool")
    # result = docker_manifest_tool._run(
    #     repository="library/redis",
    #     tag="latest"
    # )
    
    # print(result)
    # print(type(result))
    # pprint(result)

    # docker_image_details_tool = get("docker_image_details_tool")
    # result = docker_image_details_tool._run(
    #     repository="library/redis",
    #     digest="sha256:860da63e75fbff07bcbf9a94dadb4c7eb5016427b56b124d6becd5e9c95573c0"
    # )
    # pprint(result)
    # print(type(result))

    pullable_digest_tool = get("docker_pullable_digest_tool")
    result = pullable_digest_tool._run(
        repository="library/redis",
        tag="latest"
    )
    pprint(result)
    print(type(result))
