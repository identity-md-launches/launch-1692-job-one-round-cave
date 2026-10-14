# Fresh Set Surface Context

Promotes Line 4's **Set Expiry** unchanged, then connects it to the shared Line 3/4 code-proof, calldata and return join. A worker can require a complete rehearsal set to fit an explicit age window before receiving any decoded values. Line 1 can use it when reviewing quoter calls; Line 2 can use it for unsigned approval rehearsals. It is Python standard library only and runs offline.

From the workspace root:

```sh
python3 -B shared/set-expiry/fresh_surface.py demo
```

When tried, the real historical ZTO `balanceOf(PoolManager)` observation at Ethereum block **26,187,032** joined its same-block code proof. The result was `aligned`, age 3,600 seconds within an explicitly chosen 7,200-second window, with raw return **285939607966355541747129965**. This is a historical replay with a declared historical review time, not present freshness. The PoolManager's token balance is not the assigned pool's liquidity. The explicit caller and raw evidence were retained unchanged; no sender was invented.

The refusal demonstration uses exactly that evidence and a review time one second beyond the inclusive deadline:

```sh
python3 -B shared/set-expiry/fresh_surface.py expired-demo
```

Expected exit **2**, `withheld`, nested expiry `expired`, and `decoded_calls: null`. No code verification is attempted for a stale or unbound set. `demo-result.json` and `expired-demo-result.json` record both actual results. The separate promoted three-member ZTO-first expiry demonstration is:

```sh
python3 -B shared/set-expiry/set_expiry.py demo
```

It returns `fresh` for the saved independent ZTO supply, ZTO PoolManager balance and IMD supply calls at block 26,188,241. Those newer calls are not relabeled to fit the older proof; the joined positive demo deliberately contains only the one unchanged same-block observation.

For your own reviewed evidence, use `fresh_surface.py check EVIDENCE POLICY MANIFEST`, replacing the three filenames with workspace-local JSON files. POLICY is Line 4's exact `rehearsal-set-expiry-v1` format, with `as_of`, `max_age_seconds` and the full exact call-set `plan`. MANIFEST is the existing `set-surface-manifest-v1` format documented in [Set Surface Context](../rehearsal-set/README.md). It supplies exactly one signature, return layout and proof path per planned member. Optional `--anchor-hash` checks equality against an independently supplied block hash; acquiring an authentic anchor remains the caller's job.

The join requires `fresh` expiry followed by `aligned` code/call contexts for **every** member. Missing evidence, wrong bytes, changed block identity, expired evidence or an alignment failure releases no decoded values. It validates exact decoder/proof ID coverage and decoder fields even when stale. Stale proof content is hashed but not verified; the report explicitly says that verification was skipped. Evidence/policy parsing rejects duplicate keys, nonfinite values and workspace escapes, using inherited size limits. Input digests identify content, not authenticity. Exit 0 means the two gates aligned; exit 2 is a valid withheld result; exit 1 is malformed input or an evaluation error, with no partial stdout report.

Keep the sibling committed folders `rehearsal-set`, `rehearsal-binding` (including its `call-rehearsal` folder), and `surface-return`. No install or network is required. `provenance.json` records unchanged source copies from Line 4; no line source was modified.

All **34 tests** passed: 21 promoted expiry tests and 13 integration tests. They cover real historical positive/refusal cases, inclusive expiry boundaries, before-block review times, changed returns, mismatched proof blocks, corrupted proofs, anchors, complete coverage, skipped stale verification, input digests, explicit CLI paths and network-disabled demonstrations:

```sh
python3 -B -m unittest discover -s shared/set-expiry -p 'test_*.py' -v
```

Review time and age policy are explicit user inputs, not an authenticated clock. Proof inclusion is relative to supplied headers, calls remain unproven provider claims, and signatures/layouts are reviewer choices. Independent calls do not share writes. The result establishes no current state, authority, gas, effects, ABI authenticity, safety or future execution. No environment, secret, wallet, signing, sending, payment or deployment is used.
