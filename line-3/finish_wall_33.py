"""One-time artifact assembly: retain new pigments, preserve ancestor pixels.

Requires recovered record-32 wall.png and imagegen output wall-v13.png.
Not a dependency of Code Calls. Reads only workspace files.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('thumbnail', ROOT / 'shared/wall-thumbnail/thumbnail.py')
thumbnail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbnail)
ancestor_path = ROOT / 'artifacts/line-3/wall.png'
generated_path = ROOT / 'artifacts/line-3/wall-v13.png'
ancestor_bytes = ancestor_path.read_bytes()
generated_bytes = generated_path.read_bytes()
assert hashlib.sha256(ancestor_bytes).hexdigest() == 'f4408d3615fca1b0eb14e46880c4687905e38533b133e5c150ef8a229f2d82c4'
width, height, ancestor = thumbnail.png_rgb(ancestor_path)
gw, gh, generated = thumbnail.png_rgb(generated_path)
assert (width, height) == (gw, gh) == (1254, 1254)
# Empty ancestral rock only. No previous painted mark intersects these patches.
boxes = [(425, 8, 522, 91), (520, 33, 615, 82)]
rows = [bytearray(row) for row in ancestor]
for py in range(height):
    for px in range(width):
        weights = [min(5, px-x0, x1-1-px, py-y0, y1-1-py)
                   for x0, y0, x1, y1 in boxes if x0 <= px < x1 and y0 <= py < y1]
        if not weights:
            continue
        weight = max(weights)
        for channel in range(3):
            index = 3 * px + channel
            rows[py][index] = (ancestor[py][index] * (5-weight)
                               + generated[py][index] * weight + 2) // 5


def chunk(kind, payload):
    return (struct.pack('>I', len(payload)) + kind + payload
            + struct.pack('>I', zlib.crc32(kind + payload)))


png = (b'\x89PNG\r\n\x1a\n'
       + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
       + chunk(b'IDAT', zlib.compress(b''.join(b'\0' + row for row in rows), 9))
       + chunk(b'IEND', b''))
inside = outside = 0
for py in range(height):
    for px in range(width):
        if rows[py][3*px:3*px+3] != ancestor[py][3*px:3*px+3]:
            if any(x0 <= px < x1 and y0 <= py < y1 for x0, y0, x1, y1 in boxes):
                inside += 1
            else:
                outside += 1
assert inside > 0 and outside == 0
generated_path.write_bytes(png)
ancestor_path.write_bytes(png)
jpeg = thumbnail.jpeg(thumbnail.resize(width, height, rows, 512))
assert len(jpeg) < 100000
with (ROOT / 'dist/line-3/33.jpg').open('xb') as stream:
    stream.write(jpeg)
report = {
    'ancestor_sha256': hashlib.sha256(ancestor_bytes).hexdigest(),
    'generated_before_assembly_sha256': hashlib.sha256(generated_bytes).hexdigest(),
    'wall_sha256': hashlib.sha256(png).hexdigest(), 'format': 'PNG',
    'dimensions': [width, height], 'mode': 'RGB', 'wall_bytes': len(png),
    'addition_boxes_xyxy': boxes, 'changed_pixels_inside_boxes': inside,
    'changed_pixels_outside_boxes': outside,
    'thumbnail': {'path': 'dist/line-3/33.jpg', 'format': 'JPEG', 'dimensions': [512, 512],
                  'bytes': len(jpeg), 'sha256': hashlib.sha256(jpeg).hexdigest()},
    'manual_review_pending': True, 'unmet_visual_requirements': [],
}
(ROOT / 'line-3/visual-checks-33.json').write_text(json.dumps(report, indent=2) + '\n')
record = {'name': 'The Stone Beyond',
          'image': 'https://api.imd.fun/artifacts/' + report['wall_sha256'],
          'attributes': [
              {'trait_type': 'Cave', 'value': 'Moss'},
              {'trait_type': 'Wall', 'value': 'Line 3'},
              {'trait_type': 'Number', 'value': 33},
              {'trait_type': 'Left behind', 'value': 'Code Calls'},
              {'trait_type': 'Meaning', 'value': 'Pepe looks beyond one stone to the other stone it calls.'},
              {'trait_type': 'One thing', 'value': 'Ethereum executable code identity'}]}
with (ROOT / 'dist/line-3/33.json').open('x') as stream:
    stream.write(json.dumps(record, indent=2) + '\n')
print(json.dumps(report, indent=2))
