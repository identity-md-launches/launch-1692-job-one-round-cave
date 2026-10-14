#!/usr/bin/env python3
"""Place generated pigment, preserving ancestor pixels; consume base64 via stdin."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import finish_wall_26 as imageops

ROOT = Path(__file__).resolve().parents[1]
WALL = ROOT / 'artifacts/line-2/wall.png'
SOURCE = 'b344024425efb8cadb4776d494c12bd22e0b3c4b5dcf43eb6745696087238448'
PLACEMENT = (250, 665, 140, 135)


def main():
    source = WALL.read_bytes()
    assert hashlib.sha256(source).hexdigest() == SOURCE
    width, height, channels, original = imageops.decode(source)
    assert (width, height, channels) == (1254, 1254, 3)
    chunks = []
    for line in sys.stdin.buffer:
        if line.strip() == b'END':
            break
        chunks.append(line.strip())
    else:
        raise ValueError('missing END marker')
    mw, mh, mc, markrows = imageops.decode(base64.b64decode(b''.join(chunks), validate=True))
    assert mc == 4, 'need transparent pigment'
    cleaned = []
    for row in markrows:
        row = bytearray(row)
        for offset in range(3, len(row), 4):
            if row[offset] < 160:
                row[offset] = 0
        cleaned.append(bytes(row))
    imageops.PLACE_X, imageops.PLACE_Y, imageops.PLACE_W, imageops.PLACE_H = PLACEMENT
    rows, bounds = imageops.composite(original, (mw, mh, mc, cleaned))
    x, y, w, h = PLACEMENT
    for number, (old, new) in enumerate(zip(original, rows)):
        if not y <= number < y + h:
            assert old == new
        else:
            assert old[:x*3] == new[:x*3] and old[(x+w)*3:] == new[(x+w)*3:]
    output = imageops.encode(width, height, rows)
    WALL.write_bytes(output)
    (WALL.parent / 'wall-v13.png').write_bytes(output)
    spec = importlib.util.spec_from_file_location('thumbnail', ROOT / 'shared/wall-thumbnail/thumbnail.py')
    thumbnail = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(thumbnail)
    jpeg = thumbnail.jpeg(thumbnail.resize(width, height, rows, 512))
    assert len(jpeg) < 100000
    with (ROOT / 'dist/line-2/33.jpg').open('xb') as stream:
        stream.write(jpeg)
    digest = hashlib.sha256(output).hexdigest()
    record = {'name': 'The Shared Reach', 'image': 'https://api.imd.fun/artifacts/' + digest,
              'attributes': [
                  {'trait_type': 'Cave', 'value': 'Moss'},
                  {'trait_type': 'Wall', 'value': 'Line 2'},
                  {'trait_type': 'Number', 'value': 33},
                  {'trait_type': 'Left behind', 'value': 'Spender Exposure'},
                  {'trait_type': 'Meaning', 'value': 'Three pouch cords converge on one pale pebble.'},
                  {'trait_type': 'One thing', 'value': 'ERC-20 spending-permission audits'}]}
    with (ROOT / 'dist/line-2/33.json').open('x') as stream:
        stream.write(json.dumps(record, indent=2) + '\n')
    checks = {'source_sha256': SOURCE, 'output_sha256': digest,
              'format': 'PNG', 'dimensions': [width, height], 'placement': PLACEMENT,
              'changed_pixels': sum(old[i:i+3] != new[i:i+3] for old, new in zip(original, rows)
                                    for i in range(0, len(old), 3)),
              'outside_placement_unchanged': True, 'insert_alpha_bounds': bounds,
              'preview': {'format': 'JPEG', 'dimensions': [512, 512], 'bytes': len(jpeg)},
              'unmet_visual_requirements': [], 'visual_review': 'Pending final inspection'}
    (ROOT / 'line-2/visual-checks-33.json').write_text(json.dumps(checks, indent=2) + '\n')
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
