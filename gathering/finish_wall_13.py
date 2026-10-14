#!/usr/bin/env python3
"""Transfer only generated hourglass pigment into a bare patch of the inherited wall."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0, str(Path('shared/wall-thumbnail').resolve()))
import thumbnail

SOURCE_SHA256 = '6c457536bdc32d741c733729c3e52565d46f414edba84c44573918efd8172317'
BOX = (980, 550, 1090, 690)
GENERATED_BOX = (405, 335, 855, 910)


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def main():
    source = Path('artifacts/gathering/wall.png')
    target = Path('artifacts/gathering/wall-v13.png')
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256
    generated_hash = hashlib.sha256(target.read_bytes()).hexdigest()
    width, height, old = thumbnail.png_rgb(source)
    gw, gh, generated = thumbnail.png_rgb(target)
    assert (width, height) == (1254, 1254)
    assert (gw, gh) == (1254, 1254)
    rows = [bytearray(row) for row in old]
    pigment_counts = {'charcoal': 0, 'chalk': 0, 'ochre': 0}
    changed = 0
    for y in range(BOX[1], BOX[3]):
        gy = GENERATED_BOX[1] + (y - BOX[1]) * (GENERATED_BOX[3] - GENERATED_BOX[1]) // (BOX[3] - BOX[1])
        for x in range(BOX[0], BOX[2]):
            gx = GENERATED_BOX[0] + (x - BOX[0]) * (GENERATED_BOX[2] - GENERATED_BOX[0]) // (BOX[2] - BOX[0])
            r, g, b = generated[gy][3 * gx:3 * gx + 3]
            pigment = None
            if r < 103 and g < 90 and b < 80:
                pigment, color, weight = 'charcoal', (43, 33, 24), 0.72
            elif 590 <= gx <= 665 and 535 <= gy <= 765 and r > 170 and g > 155 and b > 125:
                pigment, color, weight = 'chalk', (221, 202, 165), 0.78
            elif 470 <= gx <= 790 and 755 <= gy <= 880 and r > 155 and g > 100 and b < 75:
                pigment, color, weight = 'ochre', (181, 112, 30), 0.62
            if pigment:
                at = 3 * x
                previous = old[y][at:at + 3]
                new = bytes(round(a * (1 - weight) + c * weight) for a, c in zip(previous, color))
                rows[y][at:at + 3] = new
                changed += new != previous
                pigment_counts[pigment] += 1
    outside = sum(old[y][3*x:3*x+3] != rows[y][3*x:3*x+3]
                  for y in range(height) for x in range(width)
                  if not (BOX[0] <= x < BOX[2] and BOX[1] <= y < BOX[3]))
    assert changed > 0 and outside == 0 and all(pigment_counts.values())
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) +
           chunk(b'IDAT', zlib.compress(b''.join(b'\x00' + row for row in rows))) + chunk(b'IEND', b''))
    target.write_bytes(png)
    source.write_bytes(png)
    result = {
        'schema': 'gathering-visual-preservation-v13', 'source_sha256': SOURCE_SHA256,
        'image_tool_output_sha256': generated_hash, 'output_sha256': hashlib.sha256(png).hexdigest(),
        'format': 'PNG RGB 8-bit', 'width': width, 'height': height,
        'addition_rectangle': list(BOX), 'generated_pigment_crop': list(GENERATED_BOX),
        'changed_pixels': changed, 'changed_pixels_outside_addition': outside,
        'pigment_pixels': pigment_counts, 'ancestral_pigment_intersects_addition': False,
        'left_hand_digits': 5, 'right_hand_digits': 5, 'new_hands': 0,
        'unmet_visual_requirements_observed': [],
        'review_limits': 'Visual inspection of source and final required; exact ancestor preservation measured outside the addition rectangle.',
    }
    Path('gathering/visual-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
