import hashlib
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

parser = argparse.ArgumentParser(description='Generate an unannotated road fixture through the normal cycling pipeline.')
parser.add_argument('--source', required=True, type=Path)
parser.add_argument('--build', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--osm', required=True, type=Path)
parser.add_argument('--expected-commit', required=True)
parser.add_argument('--region', default='Canada_British Columbia_Vancouver')
args = parser.parse_args()
host = args.source.resolve()
out = args.output.resolve()
osm = args.osm.resolve()
build = args.build.resolve()
generator = build / 'generator_tool'
region = args.region

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def git(*args):
    return subprocess.check_output(['git', *args], cwd=host, text=True).strip()

head = git('rev-parse', 'HEAD')
assert head == args.expected_commit
cache = (build / 'CMakeCache.txt').read_text()
assert 'CMAKE_HOME_DIRECTORY:INTERNAL=' + str(host) + '\n' in cache
assert not git('status', '--porcelain', '--ignore-submodules=all')
assert not out.exists()
(out / 'maps/borders').mkdir(parents=True)
(out / 'intermediate').mkdir()
shutil.copy2(host / 'data/borders' / (region + '.poly'), out / 'maps/borders')
common = [str(generator), '--threads_count=1', f'--data_path={out / "maps"}',
          f'--intermediate_data_path={out / "intermediate"}', f'--cache_path={out / "intermediate"}',
          f'--user_resource_path={host / "data"}', '--node_storage=map']
phases = [('preprocess', [f'--osm_file_name={osm}', '--osm_file_type=xml', '--preprocess=true']),
          ('features', [f'--osm_file_name={osm}', '--osm_file_type=xml', '--generate_features=true']),
          ('geometry', ['--planet_version=1786991694', '--generate_geometry=true', '--generate_index=true', f'--output={region}'])]
osm_sha, generator_sha = digest(osm), digest(generator)
elapsed = {}
for phase, flags in phases:
    start = time.monotonic()
    with (out / (phase + '.log')).open('w') as log:
        subprocess.run(common + flags, cwd=host, stdout=log, stderr=subprocess.STDOUT,
                       env={**os.environ, 'XDG_CONFIG_HOME': str(out / 'config')}, check=True)
    elapsed[phase] = time.monotonic() - start
    print(phase, elapsed[phase], flush=True)
assert git('rev-parse', 'HEAD') == head
assert digest(osm) == osm_sha and digest(generator) == generator_sha
mwm = out / 'maps' / (region + '.mwm')
(out / 'manifest.json').write_text(json.dumps(dict(
    source_commit=head, source_status=git('status', '--porcelain'),
    submodules=git('submodule', 'status', '--recursive'), osm_sha256=osm_sha,
    generator_sha256=generator_sha, map_sha256=digest(mwm), map_bytes=mwm.stat().st_size,
    generation_workers=1, memory_limit_mib=1800, swap_limit_bytes=0,
    elapsed_seconds=elapsed, scope='Normal generator, original unannotated road extract; not a routing-graph map'
), indent=2) + '\n')
