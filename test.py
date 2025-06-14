"""
pip install dxf
"""

import json, os
from dxf import DXF

registry = 'registry-1.docker.io'
repo     = 'library/nginx'
tag      = '1.27.5'          # or 'latest'
wanted_platform = ('linux', 'amd64', None)  # (os, arch, variant)

d = DXF(registry, repo, auth=(lambda *_: ('','')))  # anonymous read

# 1) Pull the *index* (manifest list) for the tag
index_str, index_digest = d.pull_manifest(tag)
index = json.loads(index_str)

if index['mediaType'] not in (
        'application/vnd.docker.distribution.manifest.list.v2+json',
        'application/vnd.oci.image.index.v1+json'):
    raise SystemExit('image is single-arch; skip down to step 3')

# 2) Pick the correct variant descriptor
def match(desc):
    p = desc.get('platform', {})
    return (p.get('os'), p.get('architecture'), p.get('variant')) == wanted_platform

variant_desc = next(filter(match, index['manifests']), None)
if not variant_desc:
    raise SystemExit(f'platform {wanted_platform} not found in manifest list')

variant_digest = variant_desc['digest']

# 3) Pull that variant’s *image manifest*
manifest_str, _ = d.pull_manifest(variant_digest)
manifest = json.loads(manifest_str)

# 4) Fetch its config blob
config_digest = manifest['config']['digest']
config_json   = json.loads(d.get_blob(config_digest))
cfg           = config_json['config']

# 5) Print the bits you map into a Pod spec
print('\n=== fields you care about ===')
print('digest (pin with @sha256):', index_digest)
print('User               :', cfg.get('User') or '(root)')
print('ExposedPorts       :', list((cfg.get('ExposedPorts') or {}).keys()))
print('Volumes            :', list((cfg.get('Volumes') or {}).keys()))
print('Entrypoint         :', cfg.get('Entrypoint'))
print('Cmd                :', cfg.get('Cmd'))
print('Env (first 3)      :', (cfg.get('Env') or [])[:3])
print('StopSignal         :', cfg.get('StopSignal'))
