#!/usr/bin/env python3
"""Create one million SYNTHETIC directed segments and compare storage encodings."""
import gzip
import json
import lzma
import random
from pathlib import Path
import struct
import sys
import time
import zlib
from generate import string, varuint

mixed = len(sys.argv) > 2 and sys.argv[2] == '--mixed'
rng = random.Random(10062)
profile_count = 4096 if mixed else 2
out = bytearray(struct.pack('<4sHHQQqq', b'OMHT', 1, 0, 1767225600, 12345, 1767225600, 1798761600))
out += string('Benchmark') + string('AAAAAAAAAAAA') + string('Synthetic benchmark; CC0; not observations')
out += struct.pack('<HHI', profile_count, 1, 1000000)
out += (bytes(rng.randrange(5, 121) for _ in range(profile_count * 168)) if mixed
        else bytes([60] * 168) + bytes([20] * 168))
out += struct.pack('<HHqi', 1, 0, 1767225600, 0)
previous = 0
for i in range(1000000):
    key = ((i // 2) << 32) | (i % 2)
    out += varuint(key if i % 64 == 0 else key - previous)
    out += struct.pack('<HBB', rng.randrange(profile_count) if mixed else i % 2, 0, 128)
    previous = key
out += struct.pack('<I', zlib.crc32(out))
Path(sys.argv[1]).write_bytes(out)
results = {'synthetic_segments': 1000000, 'mixed': mixed, 'profiles': profile_count, 'flat_key64_value32_bytes': 12000000, 'blocked_delta_bytes': len(out)}
for name, compressor in [('gzip', lambda b: gzip.compress(b, mtime=0)), ('xz', lzma.compress)]:
    start = time.perf_counter()
    result = compressor(out)
    results[name + '_bytes'] = len(result)
    results[name + '_compression_seconds'] = time.perf_counter() - start
print(json.dumps(results, indent=2))
