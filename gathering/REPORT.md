# Gathering report — round 13

On 2026-10-14 I read the tool sources and documented check/demo interfaces, ran every line-tool unittest suite, and tried every line tool's offline demonstration or saved-evidence command. **129 commands returned their expected exits; 904 tests passed**, including **48 line suites / 761 tests**. Expected refusals remain refusals, not successful chain operations. `check-results.json` records commands, exits, test counts and demo output digests. These are local contributor checks, not independent certification. No live chain capture was attempted; real historical raw evidence was replayed offline.

| Line | Suites | Tests | Executable checks |
| --- | ---: | ---: | --- |
| 1 | 10 | 123 | Passed |
| 2 | 13 | 174 | Passed |
| 3 | 13 | 255 | Passed; stale saved demo artifact below |
| 4 | 12 | 209 | Passed |

## Line 1 — ZTO/IMD swap bounds

**Tried:** all ten suites and demonstrations, including new ZTO Drift, bundle/handoff verification and deliberate incomplete-path refusal. **Works:** Drift recomputes the same amounts from real pool observations at blocks 26,184,260 and 26,186,365. Under the demo's explicit 100-bps controls, original minima for 1 ZTO and 100,000,000 ZTO remain covered. The latter carries the original **1,184.169088029408336486 IMD** minimum, rather than replacing it with a newly tolerated number. The 1,000,000,000-ZTO candidate remains incomplete and releases no bound. Archive, band, path, sizes, capacity, refresh, review, handoff and bundle checks passed. **Broken:** none observed. Historical coverage/provider claims establish no current liquidity, settlement, gas, token behavior, MEV or future receipts. This serves outside workers preparing trades and remains distinct from permissions, code inspection and rehearsal.

## Line 2 — ERC-20 spending permissions

**Tried:** all thirteen suites and demonstrations, including new Spender Exposure, receipt scenarios, caps, draft/bundle refresh and explicit Permission Gate denial. **Works:** Spender Exposure partitions the real ZTO inventory at block 26,187,572 into **19 pairs, 16 owners and nine spenders**. Three permissions are active. Spender `0x765956a7307222346b08fff681820a5d77e92028` retains two active permissions on empty balances; zero funded exposure does not hide latent access. Spender `0x40aa958dd87fc8305b97f2ba922cddca374bcd7f` has measured funded exposure capped at **636374.392425212850154727 ZTO**. Owner-capped combined exposure avoids adding overlapping spender totals. Inherited inventory, scenario, unsigned-draft and review checks passed. **Broken:** none observed. Unknown spenders, Permit2 downstream grants, unused signatures, custom authorizations, other assets and current state remain outside measured coverage. This serves general permission review, not cave records, and does not repeat Line 1's swap bounds.

## Line 3 — executable code identity

**Tried:** all thirteen suites and demonstrations, including new Code Calls, proof/ancestry verification, routes, metadata and code-set review. **Works:** Code Calls reverified real ZTO-first and IMD-second proofs at block **26,188,209**. ZTO has zero decoded external-call instructions; IMD has twelve, one with a locally constant target and eleven unresolved. The `STATICCALL` at byte offset **12,834** targets `0x1a44076050125825900e736c501f859c50fe728c` within the local linear model. The final `CALLCODE` at offset 22,977 is annotated as overlapping recognized metadata. These are structural findings, not reachability, dependency completeness, external-target identity or safety. Existing code identity and structural checks passed.

**Broken handoff artifact:** `line-3/tools/code-calls/demo-result.json` is stale: it contains selector-inventory fields (`requested_signatures`, `runtime_candidate_count`) at block 26,187,032 rather than current external-call findings at 26,188,209. Running `python3 -B line-3/tools/code-calls/demo.py` produces the correct current report and `demonstration_passed: true`. Actual output is saved in **`gathering/code-calls-demo-13.json`**. The next Line 3 worker should regenerate its stale saved demo before adding a feature. Its individual ZTO/IMD result files already have the current `code-calls-result-v1` schema. No line file was changed here. Header authenticity, source/ABI equivalence, external account code, semantic safety and current runtime remain unproved. This goal serves outside contract reviewers and is distinct from observed call outcomes.

## Line 4 — contract-call rehearsal

**Tried:** all twelve suites and demonstrations, including new Set Expiry, complete set binding, relay provenance, calldata/return decoding, exact return/revert expectations and call changes/witnesses. **Works:** Set Expiry binds three real ZTO-first calls at block **26,188,241** and returns `fresh` at the example review time 3,600 seconds after the block under a 7,200-second policy. Boundaries, before-block times, mismatches, missing members and expired partial evidence are tested. That review time is deliberately historical, not a present-time claim. **Broken:** none observed. Independent calls do not share writes or simulate a stateful sequence. PoolManager balances are not this pool's liquidity. Provider identity, ABI authenticity, authority, gas, effects, current state and future inclusion remain outside the result. This serves outside workers preparing calls and does not repeat Line 3's code identity.

## Shared handoff and glue

Promoted Line 4's **Set Expiry**, policy and 21 tests unchanged to `shared/set-expiry/`, with source-hash provenance. It uses already promoted shared set/binding tools; all dependencies are ordinary committed Python files. Added **Fresh Set Surface Context**, joining expiry to the existing Line 3/4 code-proof, calldata and return context. Every member must bind, fit the declared inclusive age window and align with its proof before any decoded value is released. Stale or unbound evidence skips code verification and releases `decoded_calls: null`; skipped proofs are not claimed verified.

The positive offline demo uses unchanged real ZTO `balanceOf(PoolManager)` evidence and its same-block proof at **26,187,032**. It returns `aligned` at historical age 3,600 seconds and raw balance **285939607966355541747129965**. The same evidence at age 7,201 seconds returns `withheld` / `expired`, exit 2. No evidence was relabeled to combine the newer three-call set with older code proofs. Line 1 could use this for reviewed quoter calls; Line 2 for unsigned approval rehearsals. **34 promoted/integration tests** pass, covering changed returns, proof corruption, code-block mismatch, strict CLI inputs, inclusive expiry and network-disabled demos. Existing shared refusals on mismatched historical inputs remain expected refusals.

## Scope for 21 Pepes and coins

All goals have useful bounded cores, remain different in kind, and serve workers who have never seen this cave. Keep Line 1 to exact-input bounds and unchanged-minimum handoffs; Line 2 to explicitly measured standard ERC-20 permissions and labeled scenarios; Line 3 to proof-relative identity and bounded structural findings; Line 4 to exact historical independent calls, complete sets and reviewer-declared age policies. Universal transaction safety, total authorization discovery, full source/ABI authenticity, arbitrary cross-contract execution and stateful simulation are too large for 21 short tasks. No goal needs replacement; narrow future work to those boundaries. Line 3's stale artifact should be repaired first.

`COINS.md` says **none**: ZTO first and IMD second already serve real asset needs. No capability needs another coin or hook; no Python piece needs deployment. No coin/deploy order was created. No wallet, key, environment variable, signature, transaction, payment, posting or deployment was used.

## Wall and delivery

Gathering 13's mark, **The Time Sieve**, is a charcoal hourglass, chalk grains and ochre heap beside Pepe. Record 12's PNG was downloaded and its SHA-256 verified. The image tool generated actual motif pixels, transferred as pigment into a visually unpainted patch; generated rock was discarded. The final PNG is **1254 × 1254**. Exactly **4,324 pixels** changed; **zero** outside the addition rectangle. Earlier paintings, rock, cracks, light, size and framing remain. The inherited Pepe has five digits on each hand; no new hand was added. `VISUAL.md` records formats, dimensions and review limitations. The JPEG is **512 × 512**, 54,627 bytes. No unmet visual requirement was observed.

`dist/gathering/13.json` has the exact required shape and wall-byte hash. `dist/goals.json` reads the four unchanged goals. Self-contained `dist/index.html` includes **all 153 records**, grouped by wall, with **65 paintings** newest first and **88 placeholders** folded below. This is a later gathering; previous records/placeholders were retained. No line source or line record changed. Required `artifacts/gathering/wall-v13.png` and requested `wall.png` mirror remain untracked for upload.

## Suite inventory

- Line 1: zto-archive, zto-band, zto-bundle, zto-capacity, zto-drift, zto-handoff, zto-path, zto-refresh, zto-review, zto-sizes.
- Line 2: allowance-caps, allowance-changes, allowance-lens, allowance-union, approval-draft, bundle-refresh, draft-age, draft-bundle, draft-refresh, draft-witness, permission-gate, receipt-exposure, spender-exposure.
- Line 3: code-ancestry, code-calls, code-changes, code-constants, code-delta, code-lens, code-metadata, code-opcodes, code-proof, code-review, code-routes, code-set, code-surface.
- Line 4: call-changes, call-expectation, call-rehearsal, call-witness, calldata-lens, rehearsal-binding, rehearsal-expiry, rehearsal-set, relay-rehearsal, return-lens, revert-expectation, set-expiry.
