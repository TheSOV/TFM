
username = "thesov"
password = "dckr_pat_TV-dYor7z43lX91g4MsBwA8I4ok"

import os, json, textwrap
from dxf import DXF
from pprint import pprint

REGISTRY = "registry-1.docker.io"
REPO     = "library/redis"          # change to any repo
TAG      = "latest"

d = DXF(REGISTRY, REPO)
d.authenticate(username=username,
               password=password,
               actions=["pull"])     # read-only is enough

manifest = d.get_manifest(TAG)

selected = json.loads(manifest["linux/386"])
# pprint(selected)

cfg_desc = selected["config"]
cfg      = d.pull_blob(cfg_desc["digest"])
# coerce to bytes if needed
if not isinstance(cfg, (bytes, bytearray)):
    cfg = b"".join(cfg)

cfg = json.loads(cfg)
pprint(cfg)   


