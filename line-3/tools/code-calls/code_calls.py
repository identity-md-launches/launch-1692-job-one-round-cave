#!/usr/bin/env python3
"""Proof-backed local EVM call-target analysis; never execute or send a call."""
import argparse
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / 'code-surface'))
import code_surface as surface

ancestry, proof, lens = surface.ancestry, surface.proof, surface.lens
MASK = (1 << 256) - 1
CALLS = {0xf1: ('CALL', 7), 0xf2: ('CALLCODE', 7),
         0xf4: ('DELEGATECALL', 6), 0xfa: ('STATICCALL', 6)}
PREVIEW = 64
# Effects whose outputs depend on runtime inputs are always unknown. Each pair
# is (consumed, produced). An unrecognized opcode clears all local knowledge.
EFFECTS = {
    0x20: (2, 1), 0x30: (0, 1), 0x31: (1, 1), 0x32: (0, 1),
    0x33: (0, 1), 0x34: (0, 1), 0x35: (1, 1), 0x36: (0, 1),
    0x37: (3, 0), 0x39: (3, 0), 0x3a: (0, 1), 0x3b: (1, 1),
    0x3c: (4, 0), 0x3d: (0, 1), 0x3e: (3, 0), 0x3f: (1, 1),
    0x40: (1, 1), 0x41: (0, 1), 0x42: (0, 1), 0x43: (0, 1),
    0x44: (0, 1), 0x45: (0, 1), 0x46: (0, 1), 0x47: (0, 1),
    0x48: (0, 1), 0x49: (1, 1), 0x4a: (0, 1),
    0x50: (1, 0), 0x51: (1, 1), 0x52: (2, 0), 0x53: (2, 0),
    0x54: (1, 1), 0x55: (2, 0), 0x59: (0, 1), 0x5a: (0, 1),
    0x5c: (1, 1), 0x5d: (2, 0), 0x5e: (3, 0),
    0xf0: (3, 1), 0xf5: (4, 1),
    **{op: (2 + op - 0xa0, 0) for op in range(0xa0, 0xa5)},
    # Signed arithmetic and exponentiation are deliberately not folded.
    0x05: (2, 1), 0x07: (2, 1), 0x0a: (2, 1), 0x0b: (2, 1),
    0x12: (2, 1), 0x13: (2, 1), 0x1d: (2, 1),
}
BINARY = {
    0x01: lambda a, b: a + b, 0x02: lambda a, b: a * b,
    0x03: lambda a, b: a - b, 0x04: lambda a, b: a // b if b else 0,
    0x06: lambda a, b: a % b if b else 0,
    0x10: lambda a, b: int(a < b), 0x11: lambda a, b: int(a > b),
    0x14: lambda a, b: int(a == b), 0x16: lambda a, b: a & b,
    0x17: lambda a, b: a | b, 0x18: lambda a, b: a ^ b,
    0x1a: lambda a, b: (b >> (8 * (31 - a))) & 255 if a < 32 else 0,
    0x1b: lambda a, b: b << a if a < 256 else 0,
    0x1c: lambda a, b: b >> a if a < 256 else 0,
}


def scan(code):
    """Start each linear segment with an unknown incoming stack prefix.

    Constants describe the target operand IF these instructions execute in this
    order without an exception. No CFG edges, memory or storage are simulated.
    JUMPDEST and control transfers discard all preceding stack knowledge.
    """
    lens.require(isinstance(code, bytes) and 0 < len(code) <= lens.MAX_CODE,
                 'runtime must contain 1 to 24576 bytes')
    lens.require(code[0] != 0xef, '0xef-prefixed code requires a different execution model')
    decoded = surface.instructions(code)
    metadata = surface.opcodes.solidity_metadata(code)
    stack, findings = [], []
    segment_start = 0
    resets = 0

    def pop():
        return stack.pop() if stack else None

    def ensure(depth):
        if len(stack) < depth:
            stack[:0] = [None] * (depth - len(stack))

    for pc, opcode, operand, complete in decoded:
        if opcode == 0x5b or opcode in (0x00, 0x56, 0x57, 0xf3, 0xfd, 0xfe, 0xff):
            stack.clear()
            segment_start = pc if opcode == 0x5b else pc + 1
            resets += 1
        elif opcode == 0x5f:
            stack.append(0)
        elif 0x60 <= opcode <= 0x7f:
            # A truncated PUSH ends the byte stream; no later call can use it.
            stack.append(int.from_bytes(operand, 'big') if complete else None)
        elif 0x80 <= opcode <= 0x8f:
            depth = opcode - 0x7f
            ensure(depth)
            stack.append(stack[-depth])
        elif 0x90 <= opcode <= 0x9f:
            depth = opcode - 0x8f
            ensure(depth + 1)
            stack[-1], stack[-1-depth] = stack[-1-depth], stack[-1]
        elif opcode in BINARY:
            a, b = pop(), pop()
            stack.append(None if a is None or b is None else BINARY[opcode](a, b) & MASK)
        elif opcode in (0x08, 0x09):
            a, b, modulus = pop(), pop(), pop()
            value = None
            if a is not None and b is not None and modulus is not None:
                value = ((a + b if opcode == 0x08 else a * b) % modulus) if modulus else 0
            stack.append(value)
        elif opcode in (0x15, 0x19):
            value = pop()
            stack.append(None if value is None else
                         (int(value == 0) if opcode == 0x15 else value ^ MASK))
        elif opcode in (0x38, 0x58):
            stack.append(len(code) if opcode == 0x38 else pc)
        elif opcode in CALLS:
            name, count = CALLS[opcode]
            arguments = [pop() for _ in range(count)]
            target = arguments[1]
            findings.append({
                'pc': pc, 'opcode': name, 'segment_start_pc': segment_start,
                'target_status': 'locally-constant' if target is not None else 'unresolved',
                'target_word': '0x' + target.to_bytes(32, 'big').hex() if target is not None else None,
                'target_address': '0x' + (target & ((1 << 160) - 1)).to_bytes(20, 'big').hex()
                                  if target is not None else None,
                'overlaps_recognized_metadata': bool(metadata and pc >= metadata['start']),
            })
            stack.append(None)  # Success bit is a runtime result.
        elif opcode in EFFECTS:
            consumed, produced = EFFECTS[opcode]
            for _ in range(consumed):
                pop()
            stack.extend([None] * produced)
        else:
            stack.clear()
            segment_start = pc + 1
            resets += 1
        if len(stack) > 1024:
            # Stack overflow cannot yield a successful execution. Clear knowledge
            # rather than wrapping or silently dropping a known operand.
            stack.clear()
            segment_start = pc + 1 + len(operand)
            resets += 1
    resolved = sum(item['target_status'] == 'locally-constant' for item in findings)
    return {'recognized_solidity_metadata': metadata, 'call_instruction_count': len(findings),
            'locally_constant_target_count': resolved,
            'unresolved_target_count': len(findings) - resolved,
            'delegation_instruction_count': sum(item['opcode'] in ('CALLCODE', 'DELEGATECALL')
                                                for item in findings),
            'call_preview': findings[:PREVIEW], 'omitted_call_count': max(0, len(findings) - PREVIEW),
            'knowledge_reset_count': resets}


def inspect(bundle, anchor_hash=None):
    checked = proof.verify(bundle, anchor_hash)
    observation = bundle['observation']
    runtimes, seen = [], {}
    for node in observation['nodes']:
        for item, role in ((node, 'candidate-path'), (node.get('beacon'), 'beacon')):
            if item is None:
                continue
            address = lens.address(item['address'])
            if address in seen:
                if role not in seen[address]['roles']:
                    seen[address]['roles'].append(role)
                continue
            code = lens.code_bytes(item['code'])
            result = {'address': address, 'code_hash': lens.fixed_hex(item['code_hash'], 32),
                      'runtime_bytes': len(code), 'roles': [role], **scan(code)}
            seen[address] = result
            runtimes.append(result)
    return {'schema': 'code-calls-result-v1', 'chain_id': 1, 'target': checked['target'],
            'code_block': ancestry.block_identity(observation['block']),
            'proof': checked, 'runtimes': runtimes,
            'external_target_code_verified': False, 'reachability_verified': False,
            'anchor_authenticity_verified': False, 'semantic_safety_verified': False,
            'scope': 'Local abstract-stack call operands in proven historical runtime bytes only. '
                     'Constants are conditional on successful linear execution within each segment. '
                     'Unknown incoming stacks, jumps, storage, memory and unsupported operations remain unresolved. '
                     'All bytes, including metadata, are analyzed; unreachable instructions can appear. '
                     'No external target account/code, complete dependency graph, call effects, proxy semantics, '
                     'consensus, finality, current state, safety or permission to transact is verified.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, help='workspace raw Code Proof bundle')
    parser.add_argument('--anchor-hash', help='independently trusted execution block hash')
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(ancestry.read_json(args.bundle), args.anchor_hash), indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError,
            IndexError, RecursionError) as error:
        print('Code Calls: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
