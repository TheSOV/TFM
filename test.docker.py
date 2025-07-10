#!/usr/bin/env python3
"""
auto_mount_until_ok.py  IMAGE[:tag]  [hold_seconds]

Iteratively start an image with *read‑only* layers, detect write‑failures, and
mount `tmpfs` for each missing writable directory until the container survives
`hold_seconds` (default 10 s).

Changes in this patch
---------------------
* **Fixed regex quoting** – double‑quotes inside the regex were not escaped,
  causing a Python syntax error.  Patterns now use single‑quoted raw strings.
* Logic remains identical (log first, promote parent dir, summary output).

Usage
-----
```bash
python auto_mount_until_ok.py nginx:latest 15
```
"""
from __future__ import annotations
import json, os, re, sys, time, docker

# ───── CLI args ─────
IMAGE = sys.argv[1] if len(sys.argv) > 1 else "nginx:latest"
HOLD  = int(sys.argv[2]) if len(sys.argv) > 2 else 10

client = docker.from_env()
api    = docker.APIClient()

print(f"Pulling image '{IMAGE}' to ensure it's available...")
client.images.pull(IMAGE)
print("✓ Image is ready.")

tmpfs_mounts: dict[str, str] = {}

# Regex patterns for typical EROFS / directory errors
_PATTERNS: list[re.Pattern] = [
    re.compile(r': (?P<path>/[^:"]+): .*read-?only file system', re.I),
    re.compile(r'"(?P<path>/[^"]+)" .*read-?only file system', re.I),
    re.compile(r'EROFS[^\n]* (?P<path>/[^ ]+)', re.I),
    re.compile(r'"(?P<path>/[^"]+)" .*Is a directory', re.I),
    re.compile(r'"(?P<path>/[^"]+)" .*Not a directory', re.I),
]

def _extract_path(logs: str) -> str | None:
    for pat in _PATTERNS:
        m = pat.search(logs)
        if m:
            return m.group('path')
    return None


def _parent_if_file(path: str) -> str:
    base = os.path.basename(path.rstrip('/'))
    if '.' in base or base.endswith(('pid', 'sock', 'db')):
        return os.path.dirname(path) or '/'
    return path.rstrip('/') or '/'


def _start() -> str:
    hc = api.create_host_config(read_only=True, tmpfs=tmpfs_mounts)
    cid = api.create_container(image=IMAGE, host_config=hc)['Id']
    api.start(cid)
    return cid

attempt = 0
while True:
    attempt += 1
    cid = _start()
    print(f'▶ attempt {attempt}: {cid[:12]} with {len(tmpfs_mounts)} tmpfs mounts')

    start = time.time(); alive = True
    while time.time() - start < HOLD:
        if not api.inspect_container(cid)['State']['Running']:
            alive = False; break
        time.sleep(1)

    logs = api.logs(cid, tail=200, stdout=True, stderr=True).decode('utf-8', 'replace')
    api.remove_container(cid, force=True)

    if alive:
        print(f'✓ survived {HOLD}s on attempt {attempt}\n')
        break

    failing = _extract_path(logs)
    if not failing:
        raise RuntimeError('Could not parse failing path. Logs:\n' + logs)

    key = _parent_if_file(failing)

    # Remove nested mounts that conflict with the new key
    for p in list(tmpfs_mounts):
        if p.startswith(key + '/') or key.startswith(p + '/'):
            tmpfs_mounts.pop(p, None)

    if key in tmpfs_mounts:
        raise RuntimeError(f'{key} already mounted but container still fails.\nLogs:\n' + logs)

    tmpfs_mounts[key] = 'rw'
    print(f'✗ added tmpfs for {key}\n')

# ───── summary ─────
paths = sorted(tmpfs_mounts)
print('Writable dirs (one per line):')
for p in paths:
    print(f'  {p}')
print('\nJSON array:')
print(json.dumps(paths, indent=2))
