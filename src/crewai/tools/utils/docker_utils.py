"""
Docker Registry Client for interacting with Docker Registry API.
This is a utility class that provides common functionality for Docker registry operations.
"""
from typing import Dict, Any, List, Optional, Tuple
import tempfile
import shutil
import tarfile
import json
import subprocess
import re
import os
import posixpath
from pprint import pprint

class DockerUtils:
    """
    Client for interacting with Docker Registry.
    This is a utility class that provides common functionality for Docker registry operations.
    """


    def _execute_docker_command(self, cmd: List[str], check: bool = True, capture_output: bool = True, text: bool = True, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """Helper to run Docker-related commands with consistent error handling."""
        try:
            # For debugging: print(f"Executing command: {' '.join(cmd)}")
            return subprocess.run(
                cmd,
                capture_output=capture_output,
                text=text,
                check=check,
                timeout=timeout
            )
        except subprocess.TimeoutExpired as e:
            # The process was killed due to a timeout.
            # We can still access stdout/stderr captured so far.
            error_message = f"Command '{' '.join(cmd)}' timed out after {timeout} seconds."
            # To allow callers to inspect partial output, we can re-raise with a custom exception or
            # simply raise a RuntimeError that includes what was captured.
            # For now, we'll include partial output in the error.
            stderr_output = e.stderr.strip() if e.stderr else "(no stderr captured)"
            stdout_output = e.stdout.strip() if e.stdout else "(no stdout captured)"
            raise RuntimeError(f"{error_message} Stderr: {stderr_output} Stdout: {stdout_output}")
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.strip() if e.stderr and capture_output else ""
            if not error_message and e.stdout and capture_output: # if stderr is empty, check stdout
                error_message = e.stdout.strip()
            raise RuntimeError(
                f"Command '{' '.join(cmd)}' failed with exit code {e.returncode}. Error: {error_message}"
            )
        except FileNotFoundError: # If 'docker' command itself is not found
            raise RuntimeError(
                f"Docker command not found. Please ensure Docker is installed and in your PATH. Command: '{' '.join(cmd)}'"
            )

    def docker_inspect(self, repository: str, tag: str = "latest") -> Dict[str, Any]:
        """
        Inspect a Docker image and return detailed information as a dictionary.
        Pulls the image if it's not available locally or if an update is available.

        Args:
            repository: Docker repository name (e.g., 'library/redis')
            tag: Image tag (default: 'latest')

        Returns:
            Dict[str, Any]: A dictionary containing detailed image information based on user's specified fields.

        Raises:
            RuntimeError: If Docker commands fail, JSON parsing fails, or essential image inspect data is not found.
        """
        image_ref = f"{repository}:{tag}" if tag else repository

        # First, try to pull the image to ensure it's up-to-date or available
        try:
            pull_cmd = ["docker", "pull", image_ref]
            self._execute_docker_command(pull_cmd)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to pull image '{image_ref}'. Docker pull command failed: {str(e)}")

        # Then inspect the image to get the details
        try:
            inspect_cmd = ["docker", "inspect", image_ref]
            result = self._execute_docker_command(inspect_cmd)
            
            try:
                inspect_data_list = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Failed to parse JSON from docker inspect for '{image_ref}': {str(e)}\nOutput: {result.stdout}")

            if not inspect_data_list or not isinstance(inspect_data_list, list) or not inspect_data_list[0]:
                raise RuntimeError(f"No inspection data found for '{image_ref}'. Output: {result.stdout}")
            
            data = inspect_data_list[0]
            config = data.get('Config', {})
            
            repo_digests = data.get("RepoDigests")
            repo_digest_value = repo_digests[0] if repo_digests and isinstance(repo_digests, list) and len(repo_digests) > 0 else None

            exposed_ports_data = config.get("ExposedPorts")
            exposed_ports_list = list(exposed_ports_data.keys()) if exposed_ports_data and isinstance(exposed_ports_data, dict) else []

            volumes_data = config.get("Volumes")
            volumes_list_or_none = list(volumes_data.keys()) if volumes_data and isinstance(volumes_data, dict) else None
            if volumes_data is None:
                 volumes_list_or_none = None
            elif not volumes_data:
                 volumes_list_or_none = []

            image_info = {
                "repo_digest": repo_digest_value,
                "user": config.get("User"),
                "exposed_ports": exposed_ports_list,
                "volumes": volumes_list_or_none,
                "entrypoint": config.get("Entrypoint"),
                "cmd": config.get("Cmd"),
                "env_vars": config.get("Env"),
                "working_dir": config.get("WorkingDir"),
                "stop_signal": config.get("StopSignal"),
                "labels": config.get("Labels"),
                "architecture": data.get("Architecture"),
                "os": data.get("Os"),
                "created": data.get("Created"),
                "docker_version": data.get("DockerVersion"),
                "size": data.get("Size"),
                "media_type": data.get("Descriptor", {}).get("mediaType") if data.get("Descriptor") else None
            }
            
            return image_info
            
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to process inspection data for '{image_ref}': {str(e)}")

    def get_image_users_and_groups(self, repository: str, tag: str = "latest") -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieves users (UID >= 100) and their primary and supplementary group details from a Docker image.

        Args:
            repository: Docker repository name (e.g., 'library/nginx')
            tag: Image tag (default: 'latest')

        Returns:
            Dict[str, List[Dict[str, Any]]]: A dictionary containing a list of 'users'.
                                            Each user dict has 'username', 'uid', 'primary_gid',
                                            'primary_group_name', and 'supplementary_groups' (a list of dicts
                                            with 'gid' and 'group_name').
        Raises:
            RuntimeError: If Docker commands fail or parsing fails.
        """
        image_ref = f"{repository}:{tag}" if tag else repository
        users_details: List[Dict[str, Any]] = []

        try:
            # Pull the image first to ensure it's available/up-to-date
            pull_cmd = ["docker", "pull", image_ref]
            self._execute_docker_command(pull_cmd)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to pull image '{image_ref}' for user/group extraction: {str(e)}")

        try:
            # Get users with UID >= 100 from /etc/passwd
            get_users_cmd = [
                "docker", "run", "--rm", image_ref,
                "awk", "-F:", "$3>=100 {print $0}", "/etc/passwd"
            ]
            result = self._execute_docker_command(get_users_cmd)
            passwd_entries = result.stdout.strip().splitlines()

            for entry in passwd_entries:
                if not entry.strip():
                    continue
                
                parts = entry.split(':')
                if len(parts) < 4: # username:password_x:UID:GID:...
                    print(f"Warning: Skipping malformed /etc/passwd entry in {image_ref}: {entry}")
                    continue

                username = parts[0]
                uid = parts[2]
                primary_gid = parts[3]
                user_info: Dict[str, Any] = {
                    "username": username,
                    "uid": uid,
                    "primary_gid": primary_gid,
                    "primary_group_name": None,
                    "supplementary_groups": []
                }

                # Get primary group name
                try:
                    get_primary_group_cmd = ["docker", "run", "--rm", image_ref, "getent", "group", primary_gid]
                    group_result = self._execute_docker_command(get_primary_group_cmd)
                    primary_group_entry = group_result.stdout.strip()
                    if primary_group_entry:
                        user_info["primary_group_name"] = primary_group_entry.split(':')[0]
                except RuntimeError as e:
                    print(f"Warning: Could not get primary group name for GID {primary_gid} (user {username}) in {image_ref}: {e}")
                except IndexError:
                    print(f"Warning: Malformed 'getent group {primary_gid}' output for user {username} in {image_ref}.")

                # Get all group IDs the user belongs to, then get their names
                try:
                    get_all_gids_cmd = ["docker", "run", "--rm", image_ref, "id", "-G", username]
                    all_gids_result = self._execute_docker_command(get_all_gids_cmd)
                    all_gids_for_user = all_gids_result.stdout.strip().split()

                    processed_gids_for_supp = set()
                    if user_info["primary_gid"]:
                        processed_gids_for_supp.add(user_info["primary_gid"]) # Don't add primary to supplementary list

                    for gid_str in all_gids_for_user:
                        if gid_str in processed_gids_for_supp:
                            continue
                        
                        try:
                            get_supp_group_cmd = ["docker", "run", "--rm", image_ref, "getent", "group", gid_str]
                            supp_group_result = self._execute_docker_command(get_supp_group_cmd)
                            supp_group_entry = supp_group_result.stdout.strip()
                            if supp_group_entry:
                                supp_group_name = supp_group_entry.split(':')[0]
                                user_info["supplementary_groups"].append({
                                    "gid": gid_str,
                                    "group_name": supp_group_name
                                })
                                processed_gids_for_supp.add(gid_str)
                        except RuntimeError as e:
                            print(f"Warning: Could not get group name for supplementary GID {gid_str} (user {username}) in {image_ref}: {e}")
                        except IndexError:
                            print(f"Warning: Malformed 'getent group {gid_str}' output for user {username} in {image_ref}.")
                except RuntimeError as e:
                    print(f"Warning: Could not get supplementary group IDs for user {username} in {image_ref}: {e}")
                
                users_details.append(user_info)

        except RuntimeError as e:
            raise RuntimeError(f"Failed to get user details from '{image_ref}': {str(e)}")
        except Exception as e:
            # Log the full traceback for unexpected errors if a logger is available
            # import traceback; traceback.print_exc();
            raise RuntimeError(f"An unexpected error occurred while getting user details from '{image_ref}': {str(e)}")
            
        return {"users_details": users_details}

    def discover_image_writable_locations(self, repository: str, tag: str = "latest") -> Dict[str, List[str]]:
        """Orchestrates the discovery of potential writable locations in a Docker image.

        Follows a flowchart to try different methods:
        1. Native 'find' in the image.
        2. 'find' via BusyBox injected as entrypoint.
        3. 'find' on an exported filesystem (if image is too stripped).
        Handles permission issues by attempting scans as root.
        Also includes paths identified by runtime write attempts to a read-only filesystem.

        Args:
            repository: Docker repository name.
            tag: Image tag.

        Returns:
            Dict[str, List[str]]: A dictionary with a key "potential_writable_paths"
                                 containing a sorted list of unique discovered paths.
        """
        image_ref = f"{repository}:{tag}" if tag else repository
        all_discovered_paths: set[str] = set()
        static_paths_found = False

        # Explicitly pull the image first
        try:
            pull_cmd = ["docker", "pull", image_ref]
            # print(f"Pulling image: {image_ref}") # Debug
            self._execute_docker_command(pull_cmd)
        except RuntimeError as e:
            # If pull fails, we can't proceed with this image.
            # Log or raise a more specific error, or return empty if that's preferred.
            print(f"Warning: Failed to pull image {image_ref}, cannot discover writable paths. Error: {e}")
            return {"potential_writable_paths": []}

        # --- Step 1: Try native find --- 
        # print(f"Attempting Step 1: Native find for {image_ref}") # Debug
        paths, status = self._static_find_writable_native(image_ref)
        # print(f"Step 1 Result: Status='{status}', Paths Found={len(paths)}") # Debug

        if status == "success":
            all_discovered_paths.update(paths)
            static_paths_found = True
        elif status in ["no_sh", "no_find"]:
            # Native find tools not found, try BusyBox inside the image (Step 2A)
            # print(f"Attempting Step 2A: BusyBox find (in-image) for {image_ref} (due to {status})") # Debug
            paths_bb, status_bb = self._static_find_writable_busybox(image_ref)
            # print(f"Step 2A Result: Status='{status_bb}', Paths Found={len(paths_bb)}") # Debug
            if status_bb == "success":
                all_discovered_paths.update(paths_bb)
                static_paths_found = True
            elif status_bb == "permission_denied":
                # print(f"Attempting Step 2C (BusyBox as root) for {image_ref} (due to {status_bb})") # Debug
                paths_bb_root, status_bb_root = self._static_find_writable_busybox(image_ref, user="0")
                # print(f"Step 2C (BusyBox as root) Result: Status='{status_bb_root}', Paths Found={len(paths_bb_root)}") # Debug
                if status_bb_root == "success":
                    all_discovered_paths.update(paths_bb_root)
                    static_paths_found = True
                else:
                    print(f"Warning: In-image BusyBox find failed as default user ({status_bb}) and as root ({status_bb_root}) for {image_ref}.")
            elif status_bb == "no_find_in_busybox":
                 print(f"Note: Native find tools missing, and BusyBox 'find' also not found or usable in {image_ref}.")
            elif status_bb.startswith("error:"):
                print(f"Warning: In-image BusyBox find failed for {image_ref}: {status_bb}")
        elif status == "permission_denied":
            # Native find failed due to permissions, try native find as root (Step 2C)
            # print(f"Attempting Step 2C: Native find as root for {image_ref} (due to {status})") # Debug
            paths_root, status_root = self._static_find_writable_native(image_ref, user="0")
            # print(f"Step 2C (Native as root) Result: Status='{status_root}', Paths Found={len(paths_root)}") # Debug
            if status_root == "success":
                all_discovered_paths.update(paths_root)
                static_paths_found = True
            elif status_root in ["no_sh", "no_find"]:
                # Native find as root also failed due to missing tools, try in-image BusyBox as root
                # print(f"Attempting Step 2C (BusyBox as root) for {image_ref} (due to {status_root} after native root attempt)") # Debug
                paths_bb_root, status_bb_root = self._static_find_writable_busybox(image_ref, user="0")
                # print(f"Step 2C (BusyBox as root) Result: Status='{status_bb_root}', Paths Found={len(paths_bb_root)}") # Debug
                if status_bb_root == "success":
                    all_discovered_paths.update(paths_bb_root)
                    static_paths_found = True
                else:
                    print(f"Warning: Native find failed (permission denied then {status_root} as root), and in-image BusyBox as root also failed ({status_bb_root}) for {image_ref}.")
            elif status_root.startswith("error:"):
                 print(f"Warning: Native find as root failed for {image_ref}: {status_root}")
        elif status.startswith("error:"):
            print(f"Warning: Initial native find failed for {image_ref}: {status}.")

        if not static_paths_found:
            # This message will now appear if all attempted static methods (native, in-image busybox, root variations) fail to find paths.
            print(f"Note: No statically identifiable world-writable directories found for {image_ref} via any in-image find methods.")

        # --- Step 3: OPTIONAL - Check attempted writes (runtime errors) ---
        # print(f"Attempting Step 3: Runtime write attempts for {image_ref}") # Debug
        try:
            runtime_results = self._discover_runtime_write_attempts(repository, tag)
            runtime_paths = runtime_results.get("potential_write_paths", [])
            # print(f"Step 3 Result: Paths Found={len(runtime_paths)}") # Debug
            if runtime_paths:
                all_discovered_paths.update(runtime_paths)
        except RuntimeError as e:
            print(f"Warning: Runtime write attempt discovery failed for {image_ref}: {e}")
        
        return {"potential_writable_paths": sorted(list(all_discovered_paths))}

    def _static_find_writable_native(self, image_ref: str, user: Optional[str] = None) -> Tuple[List[str], str]:
        """Step 1 & 2C (native part): Find world-writable dirs using image's own find and sh."""
        find_cmd_str = 'find / -xdev -perm -0002 -type d -print'
        cmd = ['docker', 'run', '--rm']
        if user:
            cmd.extend(['--user', user])
        cmd.extend([image_ref, 'sh', '-c', find_cmd_str])

        try:
            result = self._execute_docker_command(cmd, check=True, timeout=60)
            paths = [posixpath.normpath(p) for p in result.stdout.strip().splitlines() if p.strip()]
            return sorted(list(set(paths))), "success"
        except RuntimeError as e:
            err_lower = str(e).lower()
            if "sh: not found" in err_lower or "executable file not found in $path" in err_lower and "sh" in err_lower:
                return [], "no_sh"
            if "find: not found" in err_lower or "executable file not found in $path" in err_lower and "find" in err_lower:
                return [], "no_find"
            if "permission denied" in err_lower:
                return [], "permission_denied"
            # print(f"_static_find_writable_native failed for {image_ref} (user: {user}): {e}") # Debug
            return [], f"error: {str(e)}"

    # ------------------------------------------------------------------ #
    # 1) BusyBox inside the image                                        #
    # ------------------------------------------------------------------ #
    def _static_find_writable_busybox(
        self, image_ref: str, user: Optional[str] = None
    ) -> Tuple[List[str], str]:
        """
        Run BusyBox *inside* the target image and list world-writable dirs.

        Returns (sorted_paths, status)
            status == "success"            → paths is valid
                   == "no_busybox"         → ENTRYPOINT busybox missing
                   == "no_find_in_busybox" → busybox exists but 'find' applet missing
                   == "permission_denied"  → ran as non-root and couldn't stat /
                   == "error: <details>"   → unexpected
        """
        cmd = ["docker", "run", "--rm", "--entrypoint", "busybox"]
        if user:
            cmd += ["--user", user]
        cmd += [image_ref, "find", "/", "-xdev", "-perm", "-0002", "-type", "d", "-print"]

        proc = self._execute_docker_command(cmd, timeout=60)

        # ENTRYPOINT 'busybox' not found at all
        if "executable file not found" in proc.stderr.lower():
            return [], "no_busybox"

        # BusyBox runs but the 'find' applet is missing
        if "find: not found" in proc.stderr.lower():
            return [], "no_find_in_busybox"

        if proc.returncode != 0:
            if "permission denied" in proc.stderr.lower():
                return [], "permission_denied"
            return [], f"error: exit {proc.returncode}: {proc.stderr.strip()}"

        paths = sorted(
            {posixpath.normpath(p) for p in proc.stdout.splitlines() if p.strip()}
        )
        return paths, "success"

    # ------------------------------------------------------------------ #
    # 2) Export layer – works even if image lacks BusyBox or a shell     #
    # ------------------------------------------------------------------ #
    def _static_find_writable_export(
        self, image_ref: str
    ) -> Tuple[List[str], str]:
        """
        1. docker create IMAGE   (do *not* start it)
        2. docker run --rm --volumes-from <ID>:ro busybox find …
        3. return list of world-writable directories

        Output: (sorted_paths, status)
            status == "success"
                     "busybox_pull_failed"
                     "error: <details>"
        """
        container_id: Optional[str] = None

        try:
            # 1) docker create
            proc = self._execute_docker_command(["docker", "create", image_ref])
            if proc.returncode != 0:
                return [], f"error: docker create failed: {proc.stderr.strip()}"
            container_id = proc.stdout.strip()

            # 2) run a BusyBox helper container that mounts the fs read-only
            cmd_find = [
                "docker", "run", "--rm",
                "--volumes-from", f"{container_id}:ro",
                "busybox",                     # will pull if missing
                "find", "/", "-xdev", "-perm", "-0002",
                "-type", "d", "-print",
            ]
            proc_find = self._execute_docker_command(cmd_find)

            # Could not pull / execute BusyBox image
            if proc_find.returncode != 0:
                msg = proc_find.stderr.lower()
                if "image pull" in msg or "not found" in msg:
                    return [], "busybox_pull_failed"
                return [], f"error: busybox find failed: {proc_find.stderr.strip()}"

            # 3) normalise paths
            paths = sorted(
                {posixpath.normpath(p) for p in proc_find.stdout.splitlines() if p.strip()}
            )
            return paths, "success"

        except Exception as exc:
            return [], f"error: {exc}"

        finally:
            if container_id:
                self._execute_docker_command(["docker", "rm", "-f", container_id])

    def _discover_runtime_write_attempts(self, repository: str, tag: str = "latest") -> Dict[str, List[str]]:
        """
        Discovers paths an image attempts to write to at runtime when its filesystem is read-only.
        These paths are good candidates for volume mounts (e.g., emptyDir) in Kubernetes.

        Args:
            repository: Docker repository name (e.g., 'library/nginx')
            tag: Image tag (default: 'latest')

        Returns:
            Dict[str, List[str]]: A dictionary with a key "potential_write_paths"
                                 containing a list of unique, normalized paths.
        Raises:
            RuntimeError: If critical Docker commands fail (e.g., pull).
        """
        image_ref = f"{repository}:{tag}" if tag else repository
        discovered_paths: set[str] = set()

        try:
            # Pull the image first
            pull_cmd = ["docker", "pull", image_ref]
            self._execute_docker_command(pull_cmd)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to pull image '{image_ref}' for read-only run: {str(e)}")

        try:
            # Run the image with --read-only. We expect this might fail or produce errors.
            # The command might also complete if the entrypoint handles read-only FS gracefully
            # but still logs attempted writes.
            # We set a short timeout as some images might hang indefinitely if they can't write
            # and don't exit. 30 seconds should be enough for most startup sequences.
            run_cmd = ["docker", "run", "--rm", "--read-only", image_ref]
            
            # We use check=False because the command is expected to fail or have non-zero exit code
            # if write attempts are made. We add a timeout to prevent hanging indefinitely.
            process_result = self._execute_docker_command(run_cmd, check=False, timeout=30)
            
            output_to_parse = ""
            if process_result.stdout:
                output_to_parse += process_result.stdout
            if process_result.stderr:
                output_to_parse += "\n" + process_result.stderr # Add newline to separate stdout and stderr

        except RuntimeError as e:
            # Even if _execute_docker_command itself raises (e.g. docker not found),
            # we want to catch it here. If it's a CalledProcessError due to check=True (which it isn't here),
            # the error message (e.stderr) would be the primary source.
            # Since check=False, this path is less likely for CalledProcessError unless _execute_docker_command changes.
            # For now, we assume output is in the exception string if it's a command failure.
            output_to_parse = str(e)


        # Regex patterns to find paths in "Read-only file system" errors
        # Order can matter if messages are very similar. More specific first.
        patterns = [
            r"mkdir\(\)\s*\"([^\"]+)\"\s*failed.*Read-only file system",
            r"cannot create directory\s*['\"]([^'\"]+)['\"]\s*:\s*Read-only file system",
            r"touch:\s*cannot touch\s*['\"]([^'\"]+)['\"]\s*:\s*Read-only file system",
            r"open\(\)\s*\"([^\"]+)\"\s*failed.*Read-only file system",
            r"mv:\s*cannot move\s*[^ ]*\s*to\s*['\"]([^'\"]+)['\"]\s*:\s*Read-only file system",
            r"cp:\s*cannot create regular file\s*['\"]([^'\"]+)['\"]\s*:\s*Read-only file system",
            r"ln:\s*failed to create symbolic link\s*['\"]([^'\"]+)['\"]\s*:\s*Read-only file system",
            r"can not modify\s+([^\s(]+)\s*\(read-only file system\?\)", # For messages like '... can not modify /path/to/file (read-only file system?)'
            r"Read-only file system.*Failed to create\s*['\"]?([^'\"]+)['\"]?", # General catch
            r"Failed to open\s*['\"]([^'\"]+)['\"].*Read-only file system",
            r"Permission denied.*writing to\s*['\"]([^'\"]+)['\"]", # Less specific, but common
            r"IOError: \[Errno 30\] Read-only file system: ['\"]([^'\"]+)['\"]" # Python specific
        ]

        for line in output_to_parse.splitlines():
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    path = match.group(1).strip()
                    # Normalize path using posixpath for container paths
                    normalized_path = posixpath.normpath(path)
                    if normalized_path and normalized_path != ".":
                        discovered_paths.add(normalized_path)
                    break # Found a match for this line, move to next line

        return {"potential_write_paths": sorted(list(discovered_paths))}


    def search_images_cli(
        self,
        query: str,
        limit: int = 25,
        official_only: Optional[bool] = None,
        verified_only: Optional[bool] = None,
        sort_by_stars: bool = True,
    ) -> List[Dict]:
        """Search Docker Hub images via ``docker search`` CLI.

        Parameters
        ----------
        query : str
            Search term.
        limit : int, default 25
            Maximum results to return (CLI supports up to 100).
        official_only : bool | None, default None
            If True, return only official images; False, only non-official;
            None, no filter.
        verified_only : bool | None, default None
            Filter by *verified publisher* flag similarly.
        sort_by_stars : bool, default True
            Sort results descending by stars.

        Returns
        -------
        List[Dict]
            Each dict contains ``full_name``, ``description``, ``official``,
            ``verified``, ``stars`` (int).
        """

        format_str = "{{json .}}"  # each result line as JSON

        cmd = [
            "docker",
            "search",
            "--format",
            format_str,
            "--limit",
            str(limit),
            query,
        ]

        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"docker search failed: {exc.stderr or exc.stdout}"
            ) from exc

        results: List[Dict] = []

        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Values from docker search are strings ("true" / "false")
            def _as_bool(val: str | bool | None) -> bool:
                if isinstance(val, bool):
                    return val
                if isinstance(val, str):
                    return val.lower() == "true" or val.lower() == "[ok]"
                return False

            info = {
                "full_name": item.get("Name"),
                "description": item.get("Description", ""),
                "official": _as_bool(item.get("IsOfficial")),
                "verified": _as_bool(item.get("IsTrusted")),
                "automated": _as_bool(item.get("IsAutomated")),
                "stars": int(item.get("StarCount", 0)),
            }

            if (
                (official_only is None or info["official"] == official_only)
                and (verified_only is None or info["verified"] == verified_only)
            ):
                results.append(info)

        if sort_by_stars:
            results.sort(key=lambda x: x["stars"], reverse=True)

        return results
