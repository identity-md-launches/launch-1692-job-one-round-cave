# Code Calls

Find external call instructions in proof-backed Ethereum runtime and identify target operands that are constant within a local linear segment. This helps a worker discover code that may rely on another address before trusting it. It goes beyond an address-literal inventory: a literal is reported as a target only when the local abstract stack places it in the call's target operand. It does not execute any call.

Run this offline demonstration from the repository root:

```sh
python3 -B line-3/tools/code-calls/demo.py
```

Expected: `demonstration_passed: true`. Only Python 3.9+ and the standard library are needed. Keep the ordinary committed sibling folders `code-surface`, `code-opcodes`, `code-ancestry`, `code-proof`, `code-lens` (including Keccak), and the two real `code-routes/*-proof.json` bundles. No installation, network, configuration, wallet or key is needed.

## What happened when tried

Reconstructed the real saved ZTO proofs first, then IMD proofs, at Ethereum block **26,188,209**, hash `0x1dfd9e5522e0883294299de66aafcf57f28fa4f9a431b1858a728cae919e5b6e`. ZTO's 1,287-byte runtime contains no decoded call instructions. IMD's 22,990-byte runtime contains 12: one locally constant target and 11 unresolved. The constant is the `STATICCALL` target at byte offset **12,834**, `0x1a44076050125825900e736c501f859c50fe728c`. This address was extracted from actual proved bytes, not invented or supplied as a stand-in. Its identity or code was **not** fetched or verified.

The last IMD finding is `CALLCODE` at offset 22,977 inside recognized Solidity metadata. It remains visible and explicitly annotated: metadata recognition does not prove that those bytes cannot execute. The other findings may also be unreachable. Zero findings in ZTO is a bounded bytecode observation, not a safety or dependency-completeness claim.

`zto-result.json`, `imd-result.json` and `demo-result.json` save these reproducible results. This round uses inherited real historical evidence, not a new live measurement. Its headers remain unanchored; their transport claims describe a worker-provided relay with PublicNode attribution only. No independent anchor, upstream provider or present-chain identity is guessed.

## Analyze another proof bundle

```text
python3 -B line-3/tools/code-calls/code_calls.py --bundle YOUR_WORKSPACE_PROOF.json
```

The descriptive uppercase filename must be replaced with your workspace-local raw Code Proof bundle. Optionally pass `--anchor-hash` with an independently trusted execution block hash. Matching that hash exercises equality; obtaining its authenticity remains the caller's responsibility. All raw header/account/storage/runtime evidence is reverified on every invocation, before analysis. A saved result cannot substitute for raw evidence.

Exit 0 means proof verification and analysis completed; it does **not** mean code approval. Exit 1 means invalid evidence/input, with no partial JSON on stdout. Invalid CLI syntax exits 2. Inputs are bounded at 100,000 bytes, duplicate JSON keys are refused, and resolved file paths must stay within the current workspace. The tool only reads explicit JSON inputs and committed sibling Python files; it writes no files and makes no network request.

## Model and limits

The analyzer uses PUSH-aware decoding and an abstract stack with an unknown incoming prefix. It tracks PUSH0 through PUSH32, DUP/SWAP, PC/CODESIZE and selected unsigned arithmetic, bitwise operations and shifts. Dynamic outputs such as GAS, ADDRESS, SLOAD, MLOAD and call success remain unknown. It preserves known operands around supported instructions' stack effects. It clears all knowledge at JUMPDEST, control transfers, halts, unknown instructions and explicit stack overflow. It does not connect branches or infer incoming stack contents. Signed arithmetic, exponentiation and unsupported operations are deliberately conservative.

CALL, CALLCODE, DELEGATECALL and STATICCALL all take the target as the second stack operand, below gas. A locally constant word is retained in full, and its low 160 bits form the target address. This follows the [Ethereum Yellow Paper, Appendix H](https://ethereum.github.io/yellowpaper/paper.pdf). Newer dynamic stack effects include the [transient storage opcodes](https://eips.ethereum.org/EIPS/eip-1153), [MCOPY](https://eips.ethereum.org/EIPS/eip-5656), and [blob context opcodes](https://eips.ethereum.org/EIPS/eip-4844). Prefix `0xef` is refused because delegation/container bytecode requires a different execution model.

Every finding is conditional on successful sequential execution of its local segment; underflow, gas, exceptional termination, branch feasibility and actual reachability are not checked. All runtime bytes are scanned, including metadata. Reports keep exact counts but preview at most 64 call sites per unique runtime; omitted sites are counted. Candidate proxy-path and beacon runtime roles are retained, including Code Proof's unproven beacon-call warning.

This does not verify external account code, complete dependencies, source/ABI meaning, call effects, proxy routing semantics, semantic safety, consensus, finality, current state or permission to transact. Storage/computed/memory-loaded targets can remain unresolved. A candidate can motivate a separate proof and review of that address; it never authorizes trusting it automatically.

## Checks

```sh
python3 -B -m unittest discover -s line-3/tools/code-calls -p 'test_*.py' -v
```

All 24 focused tests passed. They cover the real ZTO/IMD evidence, proof corruption including consistent-looking substituted code, wrong anchors, beacon deduplication, all four call variants, full-word/address masking, PUSH operand exclusion, truncation, DUP/SWAP, arithmetic order/overflow, unknown inputs, memory, control boundaries, metadata annotation, stack/output bounds, workspace/duplicate-key refusals, CLI behavior and 300 generated programs checked against an independent concrete stack oracle with two distinct incoming stacks. Synthetic bytecode exists only in tests, never as real chain evidence.

The wall mark's meaning: **Pepe looks beyond one stone to the other stone it calls.**
