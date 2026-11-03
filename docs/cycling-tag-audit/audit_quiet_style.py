"""Verify the promoted quiet rules against the saved OM Test package."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def line_rules(container, ignore_color):
    rules = []
    for item in container.cont:
        for element in item.element:
            for original in element.lines:
                line = copy.deepcopy(original)
                if ignore_color:
                    line.color = 0
                rules.append((item.name, element.scale, tuple(element.apply_if), str(line)))
    return sorted(rules)


def audit(repo, baseline, head, baseline_data, reference_data, reference_apk, compiler):
    sys.path.insert(0, str(compiler))
    import drules
    git = lambda *args: subprocess.check_output(['git', *args], cwd=repo)
    changed = git('diff', '--name-only', baseline, head).decode().splitlines()
    assert changed and all(path.startswith('data/') for path in changed), changed
    report = dict(baseline=baseline, head=head, changed_paths=changed, native_code_unchanged=True,
                  reference_apk_sha256=digest(reference_apk.read_bytes()), generated_files={})
    names = ['types.txt', 'classificator.txt', 'visibility.txt', 'colors.txt', 'patterns.txt']
    names += sorted(p.name for p in (repo / 'data').glob('drules_*') if p.is_file())
    with zipfile.ZipFile(reference_apk) as apk:
        for name in names:
            data = git('show', head + ':data/' + name)
            assert data == (reference_data / name).read_bytes(), name
            packaged = 'assets/' + name in apk.namelist()
            if packaged:
                assert data == apk.read('assets/' + name), name
            report['generated_files'][name] = dict(sha256=digest(data), matches_om_test_generation=True,
                                                   matches_packaged_asset=packaged)
    for name in ('types.txt', 'classificator.txt', 'patterns.txt'):
        assert git('show', baseline + ':data/' + name) == git('show', head + ':data/' + name), name
    variants = {}
    for family in ('default', 'outdoors', 'cycling', 'vehicle'):
        old_names, old = drules.load_all(baseline_data / ('drules_' + family + '.bin'))
        new_names, new = drules.load_all(repo / 'data' / ('drules_' + family + '.bin'))
        assert old_names == new_names
        for name, a, b in zip(old_names, old, new):
            assert line_rules(a, True) == line_rules(b, True), (family, name, 'line geometry')
            cycling = lambda c: [r for r in line_rules(c, False) if r[0].startswith(
                ('cyclewaytag', 'highway-cycleway', 'highway-footway-bicycle', 'highway-path-bicycle'))]
            assert cycling(a) == cycling(b), (family, name, 'cycling line rules')
            variants[family + '/' + name] = dict(line_geometry_unchanged=True, cycling_line_rules_unchanged=True)
    report['variants'] = variants
    report['scope'] = 'Generated asset and line-rule equivalence to OM Test; not full-map generation or a new GPU capture'
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('repo', 'baseline-data', 'reference-data', 'reference-apk', 'compiler', 'report'):
        parser.add_argument('--' + arg, required=True, type=Path)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--head', required=True)
    args = parser.parse_args()
    report = audit(args.repo, args.baseline, args.head, args.baseline_data, args.reference_data,
                   args.reference_apk, args.compiler)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
