# Gathering 13 image prompt

Installed image tool: `mcp__image__generate_image`, one raster generation. Its PNG was generated at the required output path, inspected, then replaced in place with the finished ancestor-preserving composition. No API/CLI fallback, wallet, key or environment variable was used.

Exact generation prompt:

> A prehistoric cave pigment motif on rough warm ochre stone, torchlit, handmade and worn, Lascaux charcoal and chalk and yellow ochre only. One small primitive hourglass symbol at the exact center of a square image: two shallow charcoal bowls pointed toward each other, upper bowl opening upward, lower bowl opening upward beneath it, joined by a narrow neck, with three tiny chalk-white grains trickling vertically through the neck and a yellow ochre heap in lower bowl. Primitive irregular burnt-stick strokes, bare stone visible within. Symbol occupies central 300 by 300 pixels; surrounding blank warm tan rock. No frame, no border, no text, no letters, no numbers, no logo, no watermark, no people, no hands. This actual pigment artwork will be composited onto an existing ancestral wall in a small blank area; do not paint other motifs.

The tool returned a 1254 × 1254 PNG despite the requested 1024 × 1024 size. Actual dimensions were checked rather than assumed. Its hourglass pigment was extracted from `[405, 335, 855, 910)` and scaled into an empty rock patch `[980, 550, 1090, 690)` of the verified gathering 12 wall. Generated background pixels were discarded. Four visible chalk grains were retained; the task does not prescribe a grain count. No ancestor figure or hand was regenerated.

`finish_wall_13.py` measures exact preservation outside that rectangle. The generated intermediate was overwritten by the whole finished wall; only the requested final PNG/mirror and numbered JPEG remain. Generated source, final PNG and final decoded JPEG were inspected. See `VISUAL.md` for dimensions, hand counts and limitations.
