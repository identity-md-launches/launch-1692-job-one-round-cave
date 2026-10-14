# Set Expiry local checks

All 12 line-tool suites passed: **209 tests**, including 21 new Set Expiry
tests. `check-results-33.json` records the exact commands and counts.
The new suite checks whole-set binding before freshness, incomplete stale sets,
exact boundaries, zero windows, pre-block review times, changed returns,
reverts, omitted callers, wrong block timestamps, duplicates, unexpected
members, policy and input limits, CLI exit categories and offline operation.

One initial test incorrectly expected uppercase hex to be rejected by the
inherited parser. Corrected the test to check normalization and retained the
existing parser behavior; the completed suite passes.

The documented offline demo exited 0 with `fresh`, three bound calls,
age 3,600 seconds, and a 7,200-second window. `tools/set-expiry/demo-result.json`
records its output. The actual historical evidence is reused unchanged from
Rehearsal Set, not recollected or relabeled. Synthetic mutations occur only in
refusal tests and are not presented as chain observations.

Wall and record checks confirm PNG 1254 × 1254, JPEG 512 × 512, exact artifact
hash, one new record (33), untouched earlier records and goal, no third-party
dependencies, and no file over 100 KB outside artifacts among delivered files.
The two wall filenames match and remain untracked. Visual limitations and
zero-pixel change outside the addition are recorded in VISUAL-33.md and
delivery-checks-33.json. These local checks are not independent certification.
