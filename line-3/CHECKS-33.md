# Local checks — Pepe 33

All 13 line-3 unittest suites passed: **255 tests**, including Code Calls' 24 tests and independent stack oracle. The new offline demonstration exited 0 with `demonstration_passed: true`. Commands, counts, exits and output are in `check-results-33.json`.

`delivery-checks-33.json` records structural checks of actual PNG/JPEG bytes, square dimensions, record schema/number/hash, unchanged GOAL.md, unchanged older records, allowed paths, source size limits, committed ordinary dependencies and untracked named PNG outputs. It independently redownloaded and hash-checked the record-32 ancestor in memory, then confirmed zero changed pixels outside the two addition rectangles.

Manual inspection of both finished images is documented in `VISUAL-33.md`; no unmet visual requirement was observed. These are local contributor results, not independent certification.

To run the useful delivered demonstration without network:

```sh
python3 -B line-3/tools/code-calls/demo.py
```
