import json
from pathlib import Path
from src.crewai.tools.yaml_tools import YAMLEditTool

def run_write_test():
    """Tests writing a full set of manifests to a new file."""
    test_file = Path("temp_write_test.yaml")
    if test_file.exists():
        test_file.unlink()

    print(f"--- Running test: Writing multiple manifests to {test_file} ---")
    edit_tool = YAMLEditTool(file_path=test_file)

    # Operations from the user's request
    operations = [ { "operation": "add_document", "value": { "apiVersion": "v1", "kind": "Namespace", "metadata": { "name": "web-server", "labels": { "name": "web-server" } } } }, { "operation": "add_document", "value": { "apiVersion": "v1", "kind": "ServiceAccount", "metadata": { "name": "nginx-serviceaccount", "namespace": "web-server", "labels": { "app": "nginx" } } } }, { "operation": "add_document", "value": { "apiVersion": "rbac.authorization.k8s.io/v1", "kind": "Role", "metadata": { "name": "nginx-role", "namespace": "web-server", "labels": { "app": "nginx" } }, "rules": [ { "apiGroups": [""], "resources": ["configmaps"], "verbs": ["get", "list", "watch"] }, { "apiGroups": [""], "resources": ["pods/log"], "verbs": ["get", "list"] } ] } }, { "operation": "add_document", "value": { "apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding", "metadata": { "name": "nginx-rolebinding", "namespace": "web-server", "labels": { "app": "nginx" } }, "subjects": [ { "kind": "ServiceAccount", "name": "nginx-serviceaccount", "namespace": "web-server" } ], "roleRef": { "kind": "Role", "name": "nginx-role", "apiGroup": "rbac.authorization.k8s.io" } } }, { "operation": "add_document", "value": { "apiVersion": "v1", "kind": "ConfigMap", "metadata": { "name": "nginx-configmap", "namespace": "web-server", "labels": { "app": "nginx" } }, "data": { "nginx.conf": "user nginx;\nworker_processes auto;\nerror_log /var/log/nginx/error.log warn;\npid /var/run/nginx.pid;\n\nevents {\n worker_connections 1024;\n}\n\nhttp {\n include /etc/nginx/mime.types;\n default_type application/octet-stream;\n sendfile on;\n keepalive_timeout 65;\n server {\n listen 8080;\n server_name localhost;\n location / {\n root /usr/share/nginx/html;\n index index.html index.htm;\n }\n }\n}\n" } } }, { "operation": "add_document", "value": { "apiVersion": "apps/v1", "kind": "Deployment", "metadata": { "name": "nginx", "namespace": "web-server", "labels": { "app": "nginx" } }, "spec": { "replicas": 3, "strategy": { "type": "RollingUpdate", "rollingUpdate": { "maxUnavailable": 1, "maxSurge": 1 } }, "selector": { "matchLabels": { "app": "nginx" } }, "template": { "metadata": { "labels": { "app": "nginx" } }, "spec": { "securityContext": { "fsGroup": 101, "runAsUser": 101, "runAsGroup": 101, "runAsNonRoot": True, "seccompProfile": { "type": "RuntimeDefault" } }, "containers": [ { "name": "nginx", "image": "nginx@sha256:dc53c8f25a10f9109190ed5b59bda2d707a3bde0e45857ce9e1efaa32ff9cbc1", "ports": [ { "containerPort": 8080 } ], "securityContext": { "allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True, "capabilities": { "drop": ["ALL"] } }, "volumeMounts": [ { "name": "nginx-config", "mountPath": "/etc/nginx/nginx.conf", "subPath": "nginx.conf", "readOnly": True } ] } ], "volumes": [ { "name": "nginx-config", "configMap": { "name": "nginx-configmap", "items": [ { "key": "nginx.conf", "path": "nginx.conf" } ] } } ], "affinity": { "podAntiAffinity": { "preferredDuringSchedulingIgnoredDuringExecution": [ { "weight": 100, "podAffinityTerm": { "labelSelector": { "matchExpressions": [ { "key": "app", "operator": "In", "values": [ "nginx" ] } ] }, "topologyKey": "kubernetes.io/hostname" } } ] } }, "serviceAccountName": "nginx-serviceaccount" } } } } }, { "operation": "add_document", "value": { "apiVersion": "v1", "kind": "Service", "metadata": { "name": "nginx", "namespace": "web-server", "labels": { "app": "nginx" } }, "spec": { "selector": { "app": "nginx" }, "ports": [ { "port": 80, "targetPort": 8080, "protocol": "TCP", "name": "http" } ], "type": "ClusterIP" } } }, { "operation": "add_document", "value": { "apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy", "metadata": { "name": "nginx-networkpolicy", "namespace": "web-server" }, "spec": { "podSelector": { "matchLabels": { "app": "nginx" } }, "policyTypes": [ "Ingress", "Egress" ], "ingress": [ { "from": [ { "podSelector": { "matchLabels": { "app.kubernetes.io/name": "ingress-nginx" } } } ] } ], "egress": [ { "ports": [ { "protocol": "TCP", "port": 80 }, { "protocol": "TCP", "port": 443 } ] } ] } } }, { "operation": "add_document", "value": { "apiVersion": "networking.k8s.io/v1", "kind": "Ingress", "metadata": { "name": "nginx-ingress", "namespace": "web-server", "annotations": { "kubernetes.io/ingress.class": "nginx" } }, "spec": { "rules": [ { "http": { "paths": [ { "path": "/", "pathType": "Prefix", "backend": { "service": { "name": "nginx", "port": { "number": 80 } } } } ] } } ] } } }, { "operation": "add_document", "value": { "apiVersion": "autoscaling/v2beta2", "kind": "HorizontalPodAutoscaler", "metadata": { "name": "nginx-hpa", "namespace": "web-server", "labels": { "app": "nginx" } }, "spec": { "scaleTargetRef": { "apiVersion": "apps/v1", "kind": "Deployment", "name": "nginx" }, "minReplicas": 3, "maxReplicas": 10, "metrics": [ { "type": "Resource", "resource": { "name": "cpu", "target": { "type": "Utilization", "averageUtilization": 60 } } } ] } } } ]

    try:
        result = edit_tool._run(operations=operations, comment="Create full web-server stack")
        print(f"\nTool Result:\n{result}")

        print("\n--- Final File Content ---")
        if test_file.exists():
            print(test_file.read_text())
        else:
            print("File was not created.")

    finally:
        # --- Cleanup ---
        print("\n--- Cleaning up test file ---")
        if test_file.exists():
            test_file.unlink()
            print(f"Removed temporary file: {test_file}")

if __name__ == "__main__":
    run_write_test()
