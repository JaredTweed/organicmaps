from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import math
import struct

def fingerprint(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def binary_sides(payload):
    if not payload:
        return '', [[], []]
    assert payload[0] == 1
    pattern = ''.join('0tls'[flag & 3] + '0frb'[(flag >> 2) & 3] for flag in payload[1:3])
    cursor = 3
    anchors = []
    for side in range(2):
        count = payload[cursor]
        cursor += 1
        points = [struct.unpack_from('<dd', bytes(payload), cursor + i * 16) for i in range(count)]
        cursor += count * 16
        anchors.append(points if pattern[side * 2] in 'tl' else [])
    assert cursor == len(payload)
    return pattern, anchors

def prototype_sides(payload):
    if not payload:
        return '', [[], []]
    version, value = bytes(payload).decode().split(':', 1)
    assert version in ('offset-bike-v1', 'offset-bike-v2')
    fields = value.split('|')
    pattern = fields[0]
    anchors = [[], []]
    for side in range(2):
        if len(fields) > side + 1 and fields[side + 1] and pattern[side * 2] in 'tl':
            anchors[side] = [tuple(map(float, pair.split(','))) for pair in fields[side + 1].split(';')]
    return pattern, anchors

def load(path, production):
    features = Counter()
    sides = defaultdict(list)
    chains = []
    header = None
    for line in path.open():
        row = json.loads(line)
        if row['kind'] == 'metadata':
            header = row
            continue
        if row['kind'] == 'chain':
            chains.append(row)
            continue
        row.pop('id')
        if isinstance(row['names'], list):
            row['names'] = {str(key): value for key, value in row['names']}
        if production:
            pattern, anchors = binary_sides(row.pop('cycling'))
        else:
            pattern, anchors = prototype_sides(row['metadata'].pop('23', []))
        key = fingerprint(row)
        features[key] += 1
        sides[key].append((pattern, [sorted(points) for points in anchors]))
    return header, features, sides, chains

parser = argparse.ArgumentParser(description='Compare prototype debug transport to production optional-section data; not a pixel audit.')
parser.add_argument('--reference', required=True, type=Path)
parser.add_argument('--candidate', required=True, type=Path)
parser.add_argument('--report', required=True, type=Path)
args = parser.parse_args()
old_header, old, old_sides, old_chains = load(args.reference, False)
new_header, new, new_sides, new_chains = load(args.candidate, True)
pattern_mismatches, anchor_mismatches, precision_mismatches = [], [], []
max_coordinate_delta = 0
old_anchor_count = new_anchor_count = 0
for values in old_sides.values():
    old_anchor_count += sum(len(points) for _, anchors in values for points in anchors)
for values in new_sides.values():
    new_anchor_count += sum(len(points) for _, anchors in values for points in anchors)
for key in old.keys() & new.keys():
    old_values = sorted(old_sides[key])
    new_values = sorted(new_sides[key])
    if [pattern for pattern, _ in old_values] != [pattern for pattern, _ in new_values]:
        pattern_mismatches.append(dict(key=key, old=old_values, new=new_values))
        continue
    for (_, old_anchors), (_, new_anchors) in zip(old_values, new_values):
        for a, b in zip(old_anchors, new_anchors):
            if len(a) != len(b):
                anchor_mismatches.append(dict(key=key, old=a, new=b))
                continue
            for p, q in zip(a, b):
                max_coordinate_delta = max(max_coordinate_delta, math.dist(p, q))
                # osm_source projects nodes before the cache truncates each
                # Mercator coordinate to 1e-7 degrees;
                # prototype Mercator anchor text was rounded to 1e-9 degrees.
                # Bound only that representation difference, not screen pixels.
                x_bound = 1e-7 + 0.5e-9 + 1e-12
                y_bound = x_bound
                if abs(p[0] - q[0]) > x_bound or abs(p[1] - q[1]) > y_bound:
                    precision_mismatches.append(dict(key=key, old=p, new=q))
report = dict(reference_export_sha256=digest(args.reference), candidate_export_sha256=digest(args.candidate),
              features_old=sum(old.values()), features_new=sum(new.values()),
              complete_feature_content_equal=(old == new),
              removed_rows=sum((old - new).values()), added_rows=sum((new - old).values()),
              pattern_mismatches=pattern_mismatches[:20], pattern_mismatch_count=len(pattern_mismatches),
              anchor_mismatches=anchor_mismatches[:20], anchor_mismatch_count=len(anchor_mismatches),
              active_anchors_old=old_anchor_count, active_anchors_new=new_anchor_count,
              maximum_anchor_coordinate_delta_degrees=max_coordinate_delta,
              anchor_precision_mismatch_count=len(precision_mismatches),
              anchor_precision_mismatches=precision_mismatches[:20],
              coordinate_contract='1e-7-degree cached Mercator coordinates versus 1e-9-degree Mercator prototype text; not a pixel tolerance',
              chains_equal=(old_chains == new_chains), chain_count_old=len(old_chains), chain_count_new=len(new_chains),
              production_sections=new_header['sections'],
              scope='Complete data comparison, not pixel-equivalent rendering proof')
args.report.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
assert old == new, 'Non-rendering feature content differs'
assert not pattern_mismatches, 'Side categories or directions differ'
assert not anchor_mismatches, 'Active junction counts differ'
assert not precision_mismatches, 'Anchor differences exceed source coordinate precision'
assert old_chains == new_chains, 'Directed phase chains differ'
