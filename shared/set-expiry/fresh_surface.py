#!/usr/bin/env python3
"""Gate the proof-backed call-set decoder on an explicit historical age policy."""
import argparse
import json
from pathlib import Path
import sys

import set_expiry as expiry

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rehearsal-set'))
import set_surface as surface

SCHEMA = 'fresh-set-surface-context-v1'
LIMITS = (
    'The explicit review time and age window are reviewer inputs, not a trusted clock. '
    'Historical provider calls and supplied proof headers are not authenticated. '
    'All calls are independent; no shared writes, atomic sequence, current state, '
    'authority, gas, effects or future execution is established. Signatures and '
    'return types are reviewer choices. Stale or unbound sets skip code verification '
    'and release no decoded values. Nothing is sent.'
)


def evaluate(saved, selected, choices, proofs, anchor_hash=None):
    chosen = expiry.policy(selected)
    ids = {entry['id'] for entry in chosen['plan']['calls']}
    require = expiry.core.require
    require(isinstance(choices, dict) and set(choices) == ids,
            'decoder choices must cover exactly every planned id')
    require(isinstance(proofs, dict) and set(proofs) == ids,
            'proofs must cover exactly every planned id')
    for choice in choices.values():
        require(isinstance(choice, dict) and set(choice) == {'signature', 'return_types'},
                'choice requires exactly signature and return_types')
        surface.surface.argument_types(choice['signature'])
        surface.surface.context.returns.layout(choice['return_types'])
    if anchor_hash is not None:
        expiry.core.data(anchor_hash, 32)
    age = expiry.evaluate(saved, chosen)
    result = {
        'schema': SCHEMA, 'verdict': 'withheld', 'reason': '',
        'expiry': age, 'surface_context': None, 'decoded_calls': None,
        'input_sha256': {
            'policy': age['policy_sha256'],
            'evidence': age['set_binding']['evidence_sha256'],
            'choices': surface.sets.binding.digest(choices),
            'proofs': {label: surface.sets.binding.digest(proofs[label]) for label in sorted(ids)},
            'anchor': surface.sets.binding.digest(anchor_hash),
        }, 'limits': LIMITS,
    }
    if age['verdict'] != 'fresh':
        result['reason'] = 'Expiry gate is ' + age['verdict'] + '; all decoded values withheld.'
    else:
        joined = surface.evaluate(saved, chosen['plan'], choices, proofs, anchor_hash)
        # Keep the full diagnostic context, but a single top-level release point.
        result['surface_context'] = {key: value for key, value in joined.items()
                                     if key != 'decoded_calls'}
        if joined['verdict'] == 'aligned':
            result['verdict'] = 'aligned'
            result['decoded_calls'] = joined['decoded_calls']
            result['reason'] = 'Complete set is inside the declared age window and every code/call context aligns.'
        else:
            result['reason'] = 'Fresh set failed code/call alignment; all decoded values withheld.'
    surface.sets.bounded(result)
    return result


def demo_inputs(expired=False):
    saved, plan, choices, proofs = surface.demo_inputs()
    block_time = int(plan['block']['timestamp'], 16)
    selected = {'schema': expiry.SCHEMA, 'as_of': hex(block_time + (7201 if expired else 3600)),
                'max_age_seconds': 7200, 'plan': plan}
    return saved, selected, choices, proofs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo', help='real ZTO evidence, historical review one hour after its block')
    commands.add_parser('expired-demo', help='same evidence reviewed one second beyond its window')
    check = commands.add_parser('check')
    check.add_argument('evidence')
    check.add_argument('policy')
    check.add_argument('manifest', help='set-surface-manifest-v1 with one proof/decoder per member')
    check.add_argument('--anchor-hash')
    args = parser.parse_args(argv)
    try:
        anchor = None
        if args.command in ('demo', 'expired-demo'):
            inputs = demo_inputs(args.command == 'expired-demo')
        else:
            read = expiry.sets.binding.read_json
            saved, selected = read(args.evidence), read(args.policy)
            choices, proofs = surface.manifest(read(args.manifest))
            inputs = saved, selected, choices, proofs
            anchor = args.anchor_hash
        result = evaluate(*inputs, anchor_hash=anchor)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result['verdict'] == 'aligned' else 2
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError,
            IndexError, RecursionError, expiry.core.RPCError) as exc:
        print(json.dumps({'schema': SCHEMA, 'verdict': 'invalid', 'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
