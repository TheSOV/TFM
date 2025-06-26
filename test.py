from src.k8s.cluster import ClusterManager
from src.k8s.kind import KindManager

import os

# kind_manager = KindManager()
# kind_manager.recreate_cluster()

cluster_manager = ClusterManager(base_dir=os.getenv("TEMP_FILES_DIR", "temp"), dir_path="project")
cluster_manager.create_namespaces(["nginx-namespace"])
c = 0
try:
    cluster_manager.create_from_directory()
except Exception as ex:
    errors = str(ex).split("\n")
    for error in errors:
        if error.strip() != "":
            c += 1
            print(f"Error {c}")
            print(error)
            print("\n")

print("All gof")