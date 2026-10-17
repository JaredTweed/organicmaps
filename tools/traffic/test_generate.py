#!/usr/bin/env python3
import copy
import csv
import gzip
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

from generate import encode, segment_key, transitions, timestamp

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = Path(__file__).resolve().parent / 'sample'


class GeneratorTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((SAMPLE / 'manifest.json').read_text())
        with (SAMPLE / 'observations.csv').open() as stream:
            self.rows = list(csv.DictReader(stream))

    def test_reproducible_cpp_fixture_and_compression(self):
        data, stats = encode(self.manifest, self.rows)
        header = (ROOT / 'libs/traffic/traffic_tests/historical_traffic_fixture.hpp').read_text()
        fixture = bytes(map(int, re.findall(r'\d+', header.split('= {')[1])))
        self.assertEqual(data, fixture)
        self.assertEqual(zlib.crc32(data[:-4]), struct.unpack('<I', data[-4:])[0])
        self.assertEqual(gzip.decompress(gzip.compress(data, mtime=0)), data)
        self.assertEqual(stats['profiles'], 3)
        self.assertEqual(encode(self.manifest, list(reversed(self.rows)))[0], data)

    def test_cli_generation_and_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'Synthetic.mwm.traffic'
            header = Path(directory) / 'fixture.hpp'
            result = subprocess.run([sys.executable, str(SAMPLE.parent / 'generate.py'),
                                     str(SAMPLE / 'manifest.json'), str(SAMPLE / 'observations.csv'),
                                     str(output), '--cpp-fixture', str(header)], check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(result.stdout)['segments'], 3)
            self.assertEqual(output.read_bytes(), encode(self.manifest, self.rows)[0])
            self.assertIn('Synthetic CC0 test data', header.read_text())
            self.assertFalse(output.with_suffix('.traffic.tmp').exists())

    def test_reject_invalid_observations(self):
        for field, value in [('speed_kmh', 'nan'), ('speed_kmh', '201'), ('speed_kmh', '0'),
                             ('samples', '0'), ('weekday', '7'), ('hour', '24'), ('id', 'unmatched')]:
            rows = copy.deepcopy(self.rows)
            rows[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                encode(self.manifest, rows)

    def test_missing_coverage_is_omitted(self):
        data, stats = encode(self.manifest, [r for r in self.rows if r['id'] == 'east'])
        self.assertEqual(stats['segments'], 1)
        self.assertEqual(stats['profiles'], 1)
        self.assertTrue(data)
        with self.assertRaises(ValueError):
            encode(self.manifest, [])

    def test_map_identity_and_duplicate_matches(self):
        for field, value in [('map_hash', ''), ('valid_until', '2025-01-01T00:00:00Z')]:
            manifest = copy.deepcopy(self.manifest)
            manifest[field] = value
            with self.assertRaises(ValueError):
                encode(manifest, self.rows)
        self.manifest['segments'].append(self.manifest['segments'][0])
        with self.assertRaises(ValueError):
            encode(self.manifest, self.rows)
        self.assertNotEqual(segment_key(7, 0, True), segment_key(7, 0, False))
        with self.assertRaises(ValueError):
            segment_key(0, 2**31, True)

    def test_dst_calendar(self):
        changes = transitions('America/Chicago', timestamp(self.manifest['valid_from']),
                              timestamp(self.manifest['valid_until']))
        self.assertEqual(changes, [(1767225600, -21600), (1772956800, -18000), (1793516400, -21600)])

    def test_dictionary_deduplication(self):
        for row in self.rows:
            row['speed_kmh'] = '50'
        _, stats = encode(self.manifest, self.rows)
        self.assertEqual(stats['profiles'], 1)
        self.assertEqual(stats['segments'], 3)


if __name__ == '__main__':
    unittest.main()
