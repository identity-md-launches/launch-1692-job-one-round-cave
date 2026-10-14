# Spender Exposure

Show which measured ERC-20 spender can reach tokens across multiple owners. This standard-library Python tool groups raw permissions by spender, retains active approvals on empty balances, and calculates exact integer exposure bounds. It helps a worker review a shared spender before funding accounts or choosing approvals to examine. ZTO is the default asset; inherited validators also support the real IMD token.

Run from the repository root, without installation or network:

```sh
python3 -B line-2/tools/spender-exposure/spender_exposure.py
```

When tried, the included real ZTO inventory at historical Ethereum block **26,187,572** produced **19 pairs across 16 owners and nine spenders**. Three permissions were active. Spender `0x765956a7307222346b08fff681820a5d77e92028` held two active permissions on empty balances; its measured funded bound was zero, so balance-based ranking alone would miss its latent access. Spender `0x40aa958dd87fc8305b97f2ba922cddca374bcd7f` had a measured funded bound of **636374.392425212850154727 ZTO**. These are saved provider observations, not a fresh measurement or a finding that either spender is malicious. `example-report.json` contains the exact default output.

Each spender total sums `min(owner balance, owner allowance to this spender)` over distinct owners. Different spenders may access the same owner's balance: **never add spender totals together**. A separate combined total first caps each owner's summed allowances at its balance, then sums distinct owners. Raw amounts are decimal strings; arithmetic and sorting use integers without floating-point rounding. Ranking uses scenario funded bound, then active permission count, then address, and conveys no trust judgment.

To use another raw Allowance Lens observation or coherent Allowance Changes inventory, supply a workspace file:

```sh
python3 -B line-2/tools/spender-exposure/spender_exposure.py --observation line-2/tools/bundle-refresh/live-after.json --receipts line-2/tools/receipt-exposure/hypothetical-one-zto.json
```

The optional receipts file follows Receipt Exposure's `permission-hypothetical-receipts-v1` schema: explicit Ethereum chain, real ZTO/IMD token address, and unique measured owners with canonical decimal `amount_raw` strings. This bundled scenario explicitly adds one hypothetical net ZTO receipt to a measured empty owner; it raises that spender's modeled bound by one ZTO. It does not describe a transfer or change a permission. Other measured owners have no hypothetical receipt. Unknown owners, mismatched tokens and overflow are refused.

Input paths must resolve inside the workspace and each file is limited to 96 KiB. Duplicate JSON keys, malformed ABI returns, duplicate pairs, inconsistent blocks/balances and precomputed reports presented as evidence are refused. SHA-256 digests bind parsed inputs, not provider authenticity. Exit 0 means the arithmetic completed; it does not authorize a transaction or certify safety. Exit 1 reports invalid evidence or a file error.

Ten focused offline tests passed:

```sh
python3 -B -m unittest discover -s line-2/tools/spender-exposure -p 'test_*.py' -v
```

The tests check real inventory partitioning, distinct-owner totals, overlapping spenders, empty-balance receipt exposure, deterministic ordering, input immutability, duplicate and malformed evidence rejection, report-as-evidence refusal, the CLI and workspace boundary. Scenario mutations are confined to tests. Ancestor tooling is reused without edits: Receipt Exposure, Permission Gate, Allowance Changes and Allowance Lens are ordinary repository source with standard-library dependencies.

Coverage is the exact measured inventory at one historical block. Unknown permissions, Permit2 downstream grants, unused signatures, custom authorization, token semantics, other assets and current state remain outside the result. Upper bounds do not prove successful execution. This tool performs offline analysis only and neither handles secrets nor signs, sends, pays, posts or deploys.
