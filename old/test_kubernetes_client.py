from kubernetes import client, config, utils
from pathlib import Path

# Load kubeconfig from default location
config.load_kube_config()
k8s_client = client.ApiClient()

manifest_path = Path("temp") / Path("k8s") / Path("nginx-deployment.yaml")

result = utils.create_from_yaml(
    k8s_client,
    str(manifest_path),
    verbose=True,
)

print(result)

# result = utils.delete_from_yaml(
#     k8s_client,
#     str(manifest_path),
#     verbose=True,
# )

print(result)