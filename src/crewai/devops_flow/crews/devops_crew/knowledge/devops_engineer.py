content = """# Ephemeral Volumes, User and Group IDs: 
Every process in a container runs with a UID and GID. By default, many container images run as the root user (UID 0) unless configured otherwise. Running as root means the process can bypass normal file permission checks (root can modify any file in the container) and potentially has the same access as root on the host if misconfigured. In contrast, running as a non-root UID means the process is subject to file ownership and mode restrictions.

Effect on File Creation: When a process creates a file inside a container, the file's owner UID/GID will match the process's UID and GID. For example, if the container is running as UID 1000 and GID 3000, any new files will be owned by 1000:3000 (user 1000, group 3000). If a volume's security context specifies a filesystem group (fsGroup), new files in that volume will be owned by that group ID (while the user ID remains the process's UID).

Volume Mounts and Host Filesystems: If you bind-mount a host directory or use certain volume types, be mindful of UID/GID mismatches. The container's UID is just a number - it might not correspond to a meaningful user on the host. For example, if a container running as UID 1000 writes to a hostPath volume, the files on the host will be owned by UID 1000 (which could be a different user on the host). Ensuring the UID/GID between host and container match (or using Kubernetes features like fsGroup) can avoid permission conflicts . In general, when using volumes, ensure the container's user has the correct permissions on the mounted directory, either by pre-setting ownership or by adjusting security context (more on this below).

For security, you may set a container's root filesystem as read-only (securityContext.readOnlyRootFilesystem: true) so that even if an attacker breaks in, they cannot modify binaries or files in the image. An immutable root filesystem significantly reduces the container's attack surface. However, most applications need some writable areas at runtime (for example, to create temporary files, write logs, or PID files). The solution is to use ephemeral writable volumes for those specific paths while keeping the rest of the filesystem read-only.

Ephemeral Volume with emptyDir: In Kubernetes, the simplest ephemeral volume is an emptyDir. An emptyDir volume is created when the pod starts (empty), lives in the node's filesystem (or memory), and is destroyed when the pod stops. By mounting an emptyDir at a specific path inside the container, you provide a writable scratch space for that container
thorsten-hans.com
. For instance, to allow writes to /tmp while everything else is read-only, you can do:

spec:
  containers:
  - name: myapp
    image: example/myapp:latest
    securityContext:
      readOnlyRootFilesystem: true
      runAsUser: 1000
      runAsNonRoot: true
    volumeMounts:
      - name: tmp-volume
        mountPath: /tmp
  volumes:
    - name: tmp-volume
      emptyDir: {}

      
Ephemeral volumes in Kubernetes can be backed by node disk or memory. In this diagram, two emptyDir volumes are mounted (one could be a tmpfs in memory). This allows writes to specific directories even when the container's root filesystem is read-only.
thorsten-hans.com

Memory-backed tmpfs: By default, emptyDir uses the node's storage (disk). If you prefer to keep data in RAM (for performance or to avoid writing to disk), you can specify emptyDir: { medium: "Memory" }. This creates a tmpfs volume backed by the node's memory
thorsten-hans.com
. The trade-off is that it consumes RAM and is non-persistent (which is fine for /tmp). For example:

  volumes:
    - name: tmp-volume
      emptyDir:
        medium: "Memory"   # Use RAM for this volume (tmpfs)


Example: The snippet below extends the earlier example for an Nginx container, demonstrating multiple emptyDir mounts for required paths:

containers:
- name: nginx
  image: nginx:alpine
  securityContext:
    readOnlyRootFilesystem: true
    runAsNonRoot: true
    runAsUser: 1000
  volumeMounts:
    - name: run-vol
      mountPath: /var/run       # for pid files, etc.
    - name: cache-vol
      mountPath: /var/cache/nginx
volumes:
  - name: run-vol
    emptyDir: {}
  - name: cache-vol
    emptyDir: {}

5.1 Kubernetes Manifest: Writable Temp Directory Example

Suppose we have a Python web application that needs a writable /tmp for caching and also writes logs to /var/log/myapp. We want to run it as non-root and with a read-only root filesystem. Below is a Kubernetes Pod spec snippet illustrating the setup:

apiVersion: v1
kind: Pod
metadata:
  name: myapp-pod
spec:
  securityContext:
    runAsUser: 1000                # Run as user ID 1000 (non-root)
    runAsGroup: 1000               # Use primary group 1000
    runAsNonRoot: true
    fsGroup: 1000                  # Files in volumes will be group-owned by 1000
  volumes:
    - name: tmp-vol
      emptyDir: { medium: "Memory" }
    - name: log-vol
      emptyDir: {}
  containers:
  - name: myapp
    image: example/myapp:latest
    securityContext:
      readOnlyRootFilesystem: true
      allowPrivilegeEscalation: false
    volumeMounts:
      - name: tmp-vol
        mountPath: /tmp            # /tmp is now writable (memory-backed)
      - name: log-vol
        mountPath: /var/log/myapp  # /var/log/myapp writable for logs

In this setup, the container runs as UID/GID 1000, which should correspond to a user created in the image (for example, our Dockerfile might have useradd -u 1000 myuser). We set readOnlyRootFilesystem: true to lock down everything except the mounted volumes. We mount an emptyDir for /tmp (using medium: Memory to improve I/O performance of temp files) and another emptyDir for the log directory. Thanks to fsGroup: 1000, Kubernetes will ensure those volume directories are owned by group 1000 and group-writable
kubernetes.io
, so our user (UID 1000, GID 1000) can write to them. The rest of the filesystem (application code, libraries, etc.) remains read-only, enhancing security.

Stateful applications often need to write to persistent storage, so file system ownership and permissions are critical. It's best practice to run containers as a non-root user and ensure the container can write to its volume:

    Use Pod SecurityContext - Define a Pod-level securityContext with a non-root user (e.g. UID 1000) and an fsGroup. For example, setting fsGroup: 1000 will make Kubernetes change the ownership of mounted volume files to group ID 1000, allowing that group to write to the volume
    kubernetes.io
    . Similarly, runAsUser: 1000 ensures the container process runs as UID 1000 instead of root. This avoids “permission denied” errors when writing to mounted volumes. The snippet below shows a sample security context:

spec:
  securityContext:
    runAsNonRoot: true        # Require non-root user
    runAsUser: 1000           # UID for the container process
    runAsGroup: 1000          # GID for primary group (optional)
    fsGroup: 1000             # Volume files owned by this group
    fsGroupChangePolicy: "OnRootMismatch"  # Optimize ownership change
  containers:
  - name: my-app
    image: example/app:latest
    securityContext:
      allowPrivilegeEscalation: false   # No privilege escalation
      capabilities:
        drop: ["ALL"]                   # Drop all Linux capabilities

Rationale: The fsGroup setting ensures any PersistentVolume or emptyDir is group-writable by GID 1000
kubernetes.io
. The container's process (UID 1000) can write to the volume as a member of that group. By dropping extraneous Linux capabilities and disallowing privilege escalation, we adhere to Kubernetes security best practices. Running as non-root is often required by cluster security policies (see Security & PodSecurity below).

Beware of HostPath Volumes - If you use a hostPath volume for quick local testing, note that hostPath volumes do not honor fsGroup or user/group SecurityContext settings in the same way managed volumes do
kubernetes.io
. Files created on the host via hostPath are typically owned by root and may not be writable by a non-root container, leading to permission errors. You have two options in this case: either run the container as root (not recommended for security) or manually adjust the directory permissions on the host
kubernetes.io
. For example, you might pre-create the host directory with chmod/chown so that UID 1000 can write to it. A safer alternative is to avoid hostPath and use a local PersistentVolume (see below) so that Kubernetes can manage permissions.

#PersistentVolumeClaims & Local Storage Best Practices

StatefulSets should use PersistentVolumeClaims (PVCs) rather than direct host paths whenever possible. PVCs provide portable, declarative storage that integrates with Kubernetes storage classes:

    Use VolumeClaimTemplates - In a StatefulSet, declare a volumeClaimTemplates section. This will automatically create a dedicated PersistentVolumeClaim for each Pod (with unique naming)
    kubernetes.io
    . For example, a StatefulSet with name “myapp” and a volume claim template named “data” will generate PVCs like “data-myapp-0”, “data-myapp-1”, etc., for each replica. Each Pod then gets its own persistent volume, avoiding conflicts. A minimal example volume claim template in a StatefulSet spec:

apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: myapp
spec:
  serviceName: myapp                     # Headless service for network identity
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 5Gi
      storageClassName: "standard"

In local clusters, the storageClassName “standard” (or another default) typically uses host-based provisioning (for example, Minikube's default StorageClass uses a hostPath provisioner under the hood). Using volumeClaimTemplates ensures each Pod's data is kept on a stable storage location that survives pod restarts.

Dynamic Provisioning vs. HostPath - Rely on dynamic storage provisioners if available. Tools like Minikube, kind, or MicroK8s often come with a default StorageClass (like “standard” or “local-path”) that will automatically provision a hostPath-backed PV when you create a PVC. This is preferable to manually using hostPath in your Pod spec, because Kubernetes will manage the lifecycle of the PV. If your local cluster has no provisioner, you can set one up (e.g. Rancher's local-path-provisioner) or manually create PersistentVolume objects of type hostPath and mark them available to be claimed. Avoid using naked hostPath volumes in production - even for local dev, treat them with caution due to the security and portability issues mentioned earlier. When you do need quick-and-dirty storage (for throwaway data), an emptyDir volume can be used (it's ephemeral, node-local storage) without the risks of hostPath.

    Local Persistent Volumes - A feature called Local PersistentVolume (storage class with provisioner: kubernetes.io/no-provisioner) allows you to manage node-local disks through PV/PVC without using raw hostPath in the Pod spec. This can be useful for multi-node clusters: you create PVs that point to directories on each node, then use volumeClaimTemplates to have each Pod bind to one. Kubernetes will schedule each Pod to the node where its PV lives (thanks to PV node affinity)
    stackoverflow.com
    stackoverflow.com
    . This gives you durable local storage but does mean pods are pinned to nodes. In a single-node dev cluster, that's not an issue. If you have no cloud volumes, local PVs are a cleaner alternative to hostPath. However, note that even local PVs have the same fundamental limitation of node affinity - if that node goes down, the Pod can't move elsewhere with its data
    stackoverflow.com
    .

    hostPath for Testing - If you do use hostPath (for example, to mount a specific host directory), use the type field to sanity-check what should exist (e.g. type: DirectoryOrCreate) and remember that PodSecurity “restricted” policy forbids hostPath volumes in Kubernetes 1.25+ by default
    kubernetes.io
    . In an unrestricted local cluster you can use them, but in a secured environment you'd need to switch to PVCs or ephemeral volumes. Always weigh whether the convenience of hostPath is worth the potential configuration drift between dev and prod.

Stable Network Identity (Headless Service & DNS)

One hallmark of StatefulSets is that each Pod gets a stable network identity. Unlike Deployment pods, which are interchangeable, StatefulSet pods have persistent DNS names that make it easy to address a specific replica. To achieve this, you should:

    Use a Headless Service - Create a Service with clusterIP: None to govern the StatefulSet's DNS domain. This headless service should have the same selector labels as the StatefulSet pods. The StatefulSet spec's serviceName field must point to this Service. With a headless service, each pod gets its own DNS A record of the form:

<statefulset_name>-<ordinal>.<service_name>.<namespace>.svc.cluster.local

For example, if your StatefulSet is named “web” and the headless Service is named “nginx”, in namespace “default”, you'll get DNS names like: web-0.nginx.default.svc.cluster.local, web-1.nginx.default.svc.cluster.local, etc.
kubernetes.io
kubernetes.io
. Clients can lookup web-0.nginx and reliably reach the first replica. The hostname of each Pod will also be set to statefulsetname-ordinal (e.g. web-0), which many stateful applications use for internal cluster membership.

Stable Ordinals - StatefulSet pods are numbered 0, 1, 2, ... N-1. These ordinals do not change over the life of the set. Even if a pod is rescheduled to a different node or restarted, it keeps the same name. This stability is useful for applications like databases or quorum systems that might use the ordinal as an identifier. You can even pass the ordinal into the container (e.g. via an environment variable derived from the hostname). The ordering also means StatefulSet pods start sequentially by default (0 up to N-1) and terminate in reverse order, unless you use the parallel pod management policy. This orchestrated startup/shutdown helps when one replica must initialize before others start (for example, a primary database must initialize before secondaries).

Accessing Pods - With the headless service in place, you can address all pods via DNS SRV or A records (for discovery), or a specific pod by using its full DNS name. For instance, a client in the same namespace can simply do ping web-2.nginx to reach the third replica. If you want a single entry point (like for clients that don't handle multiple endpoints), you can still use a separate Service (without clusterIP: None) that targets, say, the leader pod, but that's application-specific. In general, headless services plus stable DNS are the recommended way to allow StatefulSet members to find each other and communicate directly. Ensure your DNS (CoreDNS) is configured normally in your cluster (usually it is). In some local setups, you might experience a slight delay in DNS propagating for new pods (DNS negative caching can cause a ~30s delay after pod creation
kubernetes.io
), but usually this isn't problematic for most dev/test uses.

Example Headless Service YAML: To illustrate, here's a simple headless service that would work with the StatefulSet named “myapp”:

apiVersion: v1
kind: Service
metadata:
  name: myapp    # matches .spec.serviceName in StatefulSet
spec:
  clusterIP: None          # Makes it headless (no virtual IP)
  selector:
    app: myapp             # pod label selector
  ports:
    - name: http
      port: 80
      targetPort: 8080     # port your pods listen on

This service doesn't load-balance to a single IP; instead it creates DNS entries for each pod (myapp-0.myapp.default.svc.cluster.local, etc.). You can still use the Service name (myapp.default.svc.cluster.local) to get all endpoints (for example, DNS SRV records or through Kubernetes API for service endpoints). Many stateful systems (like ZooKeeper, Cassandra, etc.) rely on this pattern for node discovery.

Security Context & PodSecurity Standards

Kubernetes has moved toward stricter security by default, especially with the Pod Security Admission mechanism. When using StatefulSets in a cluster enforcing the “restricted” PodSecurity policy, you must ensure your manifests conform to certain requirements:

    Run as Non-Root - The restricted profile requires that all containers run as a non-root user. This means you should set runAsNonRoot: true (at Pod or container level) and not force any runAsUser: 0. In fact, under restricted policy, if any container is set to UID 0, the pod will be rejected
    kubernetes.io
    kubernetes.io
    . Make sure your container images support running as non-root (many official images do; if not, you might have to specify a runAsUser that matches a user inside the image). Our earlier examples already demonstrate this best practice.

    No Privilege Escalation - Restricted pods cannot allow privilege escalation (no setuid binaries gaining root privileges). Ensure each container's securityContext has allowPrivilegeEscalation: false
    kubernetes.io
    . By default, if you drop all capabilities and run as non-root, privilege escalation is naturally prevented, but it's good to be explicit. This setting is also required to satisfy the restricted policy.

    Volume Types - The restricted policy forbids hostPath volumes (as well as other hostPath-like volumes). Only certain volume types are allowed, such as PVCs, configMap, secret, downwardAPI, projected, emptyDir, etc.
    kubernetes.io
    . If your StatefulSet manifest includes a hostPath (or an inline emptyDir is fine since emptyDir is allowed), it will be denied under restricted. The solution is to use PVCs (which are allowed) or redesign to use one of the permitted volume types. In practice, this means on a restricted cluster you should rely on a PVC backed by something (it could still be a hostPath underneath via a storage class, but that indirection is what's needed to pass admission).

    Seccomp Profile - Kubernetes now demands an explicit seccomp profile in restricted mode (no running as Unconfined). Typically, the fix is to add:

securityContext:
  seccompProfile:
    type: RuntimeDefault

at the Pod or container level
kubernetes.io
. RuntimeDefault is the recommended seccomp setting which uses Docker/default seccomp filters. Ensure your pods have this, otherwise on creation you might get a complaint that seccomp is not set (depending on Kubernetes version - v1.25+ strictly enforces it).

Capabilities - Restricted pods must drop all Linux capabilities (and only allow adding back a very limited set like NET_BIND_SERVICE if needed)
kubernetes.io
kubernetes.io
. In practice, if you didn't explicitly add capabilities, you only have the default set, but the restricted policy wants you to explicitly drop ALL. It's wise to include in your container securityContext:

capabilities:
  drop: ["ALL"]

(and then add only what you require, if anything). This way, you comply with the policy and follow principle of least privilege.

PodSecurity Admission in Local Dev - If you're using a local Kubernetes (like Kind or Minikube), by default it might not enforce PodSecurity standards on the default namespace unless you opt-in. You can simulate a stricter cluster by labeling your namespace with pod-security.kubernetes.io/enforce: restricted (and the corresponding version label)
kubernetes.io
. This will cause any non-conformant pod to be rejected on creation. It's a good idea for developers to test their StatefulSet manifests under these conditions early, so you catch permission issues (running as root, hostPath usage, etc.) before deploying to a production cluster with those policies. If your pods fail to start after applying the label, use the error events to see which rule was violated (the events will say, e.g., “violates PodSecurity restricted: runAsNonRoot…”).

PodSecurityContext vs Container SecurityContext - Note that some settings can be at the pod level or container level. For example, fsGroup and runAsNonRoot are often set at the Pod level (and apply to all containers), whereas dropping capabilities and seccompProfile might need to be set for each container. Ensure you update all containers (including init containers) to satisfy the policy. Kubernetes documentation explicitly states that if any container doesn't meet the restricted criteria, the entire Pod is considered violating.

Polishing YAML for Security - Bringing it all together, a securely configured StatefulSet pod spec will include elements like:

securityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
  fsGroup: 1000
containers:
- name: my-app
  securityContext:
    runAsUser: 1000
    allowPrivilegeEscalation: false
    capabilities:
      drop: ["ALL"]

This meets the restricted requirements (non-root user, no privilege escalation, seccomp set, no extra capabilities)
kubernetes.io
kubernetes.io
. Of course, adjust the UID/GID to appropriate values for your app. Also, as noted, do not use hostPath volumes in this mode - stick to PVCs or other allowed volume types."""