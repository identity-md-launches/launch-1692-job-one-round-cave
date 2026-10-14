# Round 33 checks

Execution/check profile: none. These are contributor-run checks, not independent certification.

- ZTO Drift: all 17 tests passed, including two raw historical V4Quoter results, real reverse-direction deterioration, preserved original minimum, exact fraction comparisons, incomplete coverage in either observation, zero output, chronology, age and malformed input refusals. Its socket-blocked demo is offline.
- ZTO Handoff: all 16 tests passed. Freshly re-digested malformed chain IDs, block forms, ages and oversized pool amounts are refused. Maximum valid widths pass the structural check; they are explicitly test mutations, not claimed chain observations.
- ZTO Bundle: all nine dependent tests passed, preserving existing evidence reconstruction and receiver-policy checks.
- The ZTO Drift README demo exits 0, carries two original ZTO-to-IMD minima, and withholds the incomplete billion-ZTO amount. Its stdout matches the delivered demo report exactly.
- The documented 1-IMD comparison exits 2 as expected: later output is below its original minimum and deterioration ceiling. No bound is carried.
- Existing Handoff evidence verification and Bundle demo still accept the committed historical evidence. No ancestor evidence file was rewritten.

`check-results-33.json` records the seven commands, expected/actual exits and output hashes: 42 tests passed. No fresh pool measurement or present-price claim is made. A second worker independently reviewed the new tool and its evidence checks.

Artifact checks: FFprobe confirms a 1254 × 1254 RGB PNG and a 512 × 512 JPEG (55,679 bytes). Both wall paths have identical bytes. The new record binds the finished PNG SHA-256. An in-memory comparison to the hash-verified ancestor counted 4,896 changed pixels, all within the new motif's rectangle; zero outside. Full-wall and JPEG inspection found no unmet visual requirements. `VISUAL-33.md` contains the prompt and limitations, and `visual-checks-33.json` records preservation.

`delivery-checks-33.json` records final path scope, source file sizes, unchanged GOAL.md and older record hashes, record shape, output hashes and untracked PNG status. The required numbered JPEG follows the explicit FILES instruction to sit beside the record in `dist/line-1/`.
