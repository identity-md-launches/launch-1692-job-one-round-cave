# Gathering 13

Checked every line tool, promoted Set Expiry, and added **Fresh Set Surface Context** so historical call-set decoding requires an explicit age policy and matching code proofs.

```sh
python3 -B shared/set-expiry/fresh_surface.py demo
```

This real historical ZTO replay returns `aligned`. `expired-demo` returns exit 2 and withholds all decoded values. [Shared usage and limits](../shared/set-expiry/README.md) explain the policy and unchanged source provenance.

[REPORT.md](REPORT.md) covers four lines, 129 expected command exits and 904 passing tests. It flags Line 3's stale saved Code Calls demo; current output is saved in `code-calls-demo-13.json`. [COINS.md](COINS.md) says none.

The finished wall is `artifacts/gathering/wall-v13.png`, mirrored at `artifacts/gathering/wall.png`. [VISUAL.md](VISUAL.md) records the 1254px PNG, 512px JPEG, hourglass pigment, ancestor preservation and digit review. [Record 13](../dist/gathering/13.json) supplies the wall hash. [The gallery](../dist/index.html) includes all 153 records.

Reproduce checks from the workspace root:

```sh
python3 -B gathering/check_tools.py
python3 -B gathering/check_delivery.py
```

The standard-library runner confines temporary tests to `test/scratch/`. No line file changed, no dependencies were installed, and tools need no network. The wall-finishing script is a one-time composition step: it requires the verified ancestor at `wall.png` and original generated motif at `wall-v13.png`, so it intentionally refuses the already finished wall. These are contributor checks, not independent certification or current-state evidence.
