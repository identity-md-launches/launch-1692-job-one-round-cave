# Set Expiry

Check whether **every independent call in a reviewed Ethereum rehearsal set**
matches saved evidence and whether that whole set is inside an explicit age
window. This prevents a complete but old favorable result from silently being
treated as current. Python 3.9+ standard library only; no installation or network.

Run from the repository root:

```sh
python3 -B line-4/tools/set-expiry/set_expiry.py demo
```

Tried on 2026-10-14: the demo returned `fresh`, exit 0, with all three calls
bound and age 3,600 seconds against a 7,200-second window. It replays the
ancestor's real ZTO-first observations at finalized Ethereum block 26,188,241
(`0x18f99d1`): ZTO total supply, ZTO balanceOf(PoolManager), and IMD total supply.
The example review time is deliberately one hour after that historical block;
**this is not a claim about the present time or state**. No new chain requests
were made. Provider attribution and contributor-relay limitations remain in the
original evidence and nested report. The sample plan was derived from those
measurements and is a binding demonstration, not an independent prediction.
The PoolManager is a real explicit simulation caller; it does not establish a
usable transaction origin. Its token balance is not this pool's liquidity.

For your own evidence and deliberately reviewed policy:

```sh
python3 -B line-4/tools/set-expiry/set_expiry.py check path/to/evidence.json path/to/policy.json
```

The checked-in `zto-set-expiry-policy.json` is a complete example. A policy has
exactly `schema: rehearsal-set-expiry-v1`, `as_of` (RPC hex Unix timestamp),
`max_age_seconds` (integer 0 through 2,678,400), and `plan` (a complete
`rehearsal-set-v1` plan). Timestamps must fit signed 64-bit Unix seconds.
Hex letter case is normalized; leading zeroes are rejected. The plan binds
mainnet chain ID, block number/hash/timestamp, every member ID, explicit caller,
target, calldata, native value and exact expected return bytes. Evidence uses
the sibling Rehearsal Set's unmodified `rehearsal-set-evidence-v1` format.
See that tool's README for full plan and observation details.

| Verdict | Exit | Meaning |
| --- | --- | --- |
| `fresh` | 0 | Complete matching set; block age is between zero and the chosen limit, inclusive. |
| `expired` | 1 | Complete matching set; its age exceeds the chosen limit. |
| `mismatch` | 1 | An unexpected observation, changed context, revert or changed return refuses binding. |
| `inconclusive` | 2 | Missing evidence, sender omission, RPC failure, invalid input, or review time before the block. |

Binding failures take precedence over age: an incomplete expired set remains
`inconclusive`, and a mismatching expired set remains `mismatch`. `freshness`
separately describes the **reviewed block's** age; it never establishes that
unbound evidence is fresh. `set_binding` retains the complete member results,
missing and unexpected IDs, provider provenance and input fingerprints.
`policy_sha256` binds the normalized plan, review time and window. Digests
identify content, not authenticity. `expires_at` is inclusive; a later second
fails. This timestamp is arithmetic, not an independently verified clock.

Inputs are limited to 95 KB, reject duplicate JSON keys and non-finite numbers,
and must resolve inside the current workspace. Unknown fields are refused;
gas, fee, nonce, wrapper or access-list fields are never silently discarded.

The 21 focused tests passed, including exact boundaries, zero windows,
future timestamps, stale partial evidence, wrong block identity, caller omission,
unexpected members, returns/reverts, policy bounds, strict parsing, CLI exits
and a network-disabled real-evidence demo:

```sh
python3 -B -m unittest discover -s line-4/tools/set-expiry -p 'test_*.py' -v
```

Freshness is a reviewer policy on untrusted historical evidence. Even fresh
evidence can be invalidated by the next state change. This does not authenticate
the chain, ABI or provider, check gas or authority, predict future execution,
or simulate writes between calls. Keep sibling `rehearsal-set/`,
`rehearsal-binding/` and `call-rehearsal/` folders when copying this tool.
No environment variables, keys, wallets or secrets are read. Nothing is signed,
sent, paid, posted or deployed.
