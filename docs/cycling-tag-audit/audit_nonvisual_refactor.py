#!/usr/bin/env python3
"""Check the source boundary of the nonvisual cycling ownership refactor."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def audit(root, baseline, candidate):
    def source(revision, path):
        return subprocess.check_output(['git', 'show', revision + ':' + path], cwd=root, text=True)

    assets = ['data', 'libs/shaders']
    changed_assets = git(root, 'diff', '--name-only', baseline, candidate, '--', *assets).splitlines()
    assert not changed_assets, changed_assets
    header = 'libs/indexer/cycling_infrastructure.hpp'
    old_header = source(baseline, header)
    new_header = source(candidate, header)
    marker = 'template <typename GetTag>\n'
    codec = old_header.split(marker)[0]
    assert new_header == codec + '}  // namespace cycling\n'
    old_policy = old_header.split('  auto const negative =', 1)[1].split('\n}  // namespace cycling')[0]
    new_policy = source(candidate, 'generator/cycling_infrastructure.cpp').split('  auto const negative =', 1)[1]
    new_policy = new_policy.split('\n}  // namespace generator')[0]
    assert old_policy == new_policy
    # These are selected by actual tracked names so this audit cannot silently
    # skip an algorithm merely because its guessed filename does not exist.
    paths = git(root, 'ls-tree', '-r', '--name-only', candidate).splitlines()
    algorithms = [path for path in paths if path.startswith(('generator/', 'libs/drape_frontend/'))
                  and ('cycling_junction' in path or 'cycling_offset' in path)
                  and path.endswith(('.cpp', '.hpp'))]
    assert algorithms
    changes = git(root, 'diff', '--name-only', baseline, candidate, '--', *algorithms).splitlines()
    assert not changes, changes
    return dict(baseline=git(root, 'rev-parse', baseline), candidate=git(root, 'rev-parse', candidate),
                unchanged_asset_roots=assets, changed_assets=changed_assets,
                payload_codec_unchanged=True, osm_policy_body_moved_verbatim=True,
                osm_policy_body_sha256=hashlib.sha256(old_policy.encode()).hexdigest(),
                unchanged_algorithm_paths=algorithms,
                scope='Source ownership audit; native tests and matched-map checks are separate; not screenshot proof')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    args.report.write_text(json.dumps(audit(args.source, args.baseline, args.candidate), indent=2) + '\n')
