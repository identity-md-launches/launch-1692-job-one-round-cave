# ZTO Drift

Check whether an earlier ZTO/IMD planning minimum still fits a later observed
pool state. The tool recomputes the same independent exact-input amounts at
two real Uniswap v4 liquidity snapshots, reports the exact output change,
and carries the **original** rounded minimum only when both observations
fully cover the input and the later estimate passes the caller's limits.
It does not lower the minimum when the pool moves against the input token.

Python 3.10+, standard library only. From the repository root, one offline
command shows it working:

```sh
python3 -B line-1/tools/zto-drift/zto_drift.py --demo
```

The demonstration compares the saved real Ethereum observations at blocks
**26,184,260** and **26,186,365**, 2,105 blocks apart. It explicitly uses a
historical reference height of 26,186,365, maximum age zero, 100-bps original
slippage tolerance and 100-bps maximum output deterioration. These are
demonstration settings, not suggested amounts or tolerances.

When tried, two original minima remained covered:

| Input | Earlier estimate (IMD) | Later estimate (IMD) | Original minimum carried (IMD) |
| --- | ---: | ---: | ---: |
| 1 ZTO | 0.000015292155595473 | 0.000022505016102922 | 0.000015139234039518 |
| 100,000,000 ZTO | 1196.130391948897309582 | 1682.218759891661012097 | 1184.169088029408336486 |

The 1,000,000,000-ZTO candidate is incomplete at both snapshots, and releases
neither a bound nor a deterioration statistic. `demo-report.json` is the
actual offline output. The two 1-ZTO estimates were also checked against the
raw saved V4Quoter return words from their respective blocks. The remaining
later sizes are local recomputations, not additional measured Quoter calls.
No new chain capture or current-price claim is made.

## Compare your own observations

Supply both workspace ZTO Path snapshots and all comparison controls. ZTO
is the default input. This command demonstrates a real historical refusal
in the reverse direction:

```sh
python3 -B line-1/tools/zto-drift/zto_drift.py --before line-1/tools/zto-path/observation.json --after line-1/tools/zto-refresh/live-observation.json --input IMD --amount 1 --slippage-bps 100 --max-deterioration-bps 100 --reference-block 26186365 --max-age-blocks 0
```

It exits **2**: the original 1-IMD estimate was
63,756.931927028793174084 ZTO, its minimum was
63,119.362607758505242343 ZTO, and the later estimate is only
43,324.195593173213142556 ZTO. Both the original minimum and the separate
deterioration limit fail. Its `carried_bounds` list is empty.

Use ZTO Archive or ZTO Refresh to collect newer public evidence separately,
then replace the two paths and supply your own reference height and limits.
This comparison has no network code. It reads only named files inside the
current workspace. Keep the committed sibling `zto-review/`, `zto-sizes/`,
`zto-path/` and `zto-band/` folders; the demonstration also uses the saved
`zto-refresh/live-observation.json`. No dependency installation is needed.

## Decision rules and output

- `--amount` may repeat for 1–20 independent positive decimal amounts.
  Ordering and repeated amounts are retained by candidate index; candidates
  do not mutate liquidity or represent a sequence of trades.
- `--slippage-bps` and `--max-deterioration-bps` are explicitly chosen
  integers from 0 through 9999. The former reconstructs the original
  minimum as `floor(before_output_raw * (10000 - slippage_bps) / 10000)`.
  The latter compares `(before_output_raw - after_output_raw) * 10000 /
  before_output_raw` as an exact rational. Negative deterioration means
  output improved. The displayed integer ceiling is informational; it
  does not replace the exact comparison.
- A positive original minimum must be at most the later complete output,
  **and** deterioration must be within its separate limit, inclusively.
  A row that passes is `covered_at_later_snapshot`. Its `minimum_output_raw`
  in `carried_bounds` is the original minimum. No new tolerance is applied
  to the later output. Integer floor rounding and the exact deterioration
  filter can therefore give different decisions at tiny raw-unit boundaries.
- Incomplete coverage at either observation and an original minimum that
  rounds to zero withhold the bound. Partial outputs never become full
  outputs or drift statistics. A complete later estimate cannot repair an
  incomplete original baseline.
- Later height and timestamp must strictly increase and the block hashes
  must differ. The later snapshot must be no newer than `--reference-block`
  and no older than the supplied `--max-age-blocks`, inclusively. A failed
  chronology or age check withholds all candidate calculations and bounds.
  Older-baseline age is unrestricted because it is the explicit comparison
  baseline; its block and the gap remain visible.
- Pool identity, real currencies, fees, hook restrictions, bitmap coverage
  and tick records are validated by the ancestor decoder. Token decimals
  must agree between observations. Boolean numeric controls, malformed
  amounts, duplicate JSON keys, JSON floats/nonfinite numbers, files over
  100 KB, and paths outside the workspace cause errors.

Exit **0**, `compared`, means at least one original bound is covered under
these historical comparison settings. Inspect each candidate and
`covered_count`; this is not a claim that every requested amount passed.
Exit **2**, `refuse`, means none may be carried, including chronology or
age refusal. Exit **1** means malformed inputs or file errors. Argparse
syntax errors conventionally exit 2. JSON reports use stdout and errors
use stderr. The tool does not write files.

Snapshot SHA-256 values identify canonical parsed input JSON using the
ancestor review digest. These and the source labels do not authenticate a
provider. The caller independently chooses the observations, controls and
reference height; this is a new comparison, not proof that a previous
worker approved these settings or a verifier for an earlier handoff.
Strictly increasing headers do not prove chain ancestry or consensus.
Planning bounds do not guarantee receipts and do not model router
settlement, token transfer behavior, gas, MEV or future changes. The
numerical implementation is reused from ZTO Sizes/Path, not independently
proved here. No wallet, key, secret, environment, signature, transaction,
payment, deployment or new coin is used.

## Checks

All **17 tests passed** locally:

```sh
python3 -B -m unittest discover -s line-1/tools/zto-drift -p 'test_*.py' -v
```

They cover both raw Quoter outputs, real reverse-direction deterioration,
unchanged original minimums, exact rational thresholds, incomplete-to-full
and full-to-incomplete coverage changes, zero outputs, chronological and
age boundaries, malformed pool/decimals/header inputs, boolean controls,
ordered duplicate amounts, strict JSON parsing and offline CLI behavior.
Coverage-transition tests remove existing outer bitmap words from copied
real evidence; they do not invent successful pool responses. These are
local contributor checks, not independent certification.
