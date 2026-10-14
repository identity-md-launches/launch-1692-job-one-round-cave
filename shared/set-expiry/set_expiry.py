#!/usr/bin/env python3
"""Expire complete independent-call rehearsal sets at an explicit review time."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'expiry_rehearsal_set', HERE.parent / 'rehearsal-set' / 'rehearsal_set.py')
sets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sets)
core = sets.core
SCHEMA = 'rehearsal-set-expiry-v1'
MAX_AGE = 31 * 24 * 60 * 60
EXIT = {'fresh': 0, 'expired': 1, 'mismatch': 1, 'inconclusive': 2}
LIMITS = (
    'Fresh means only complete matching historical provider evidence inside the '
    'reviewer-declared age window. The review time is an input, not an independently '
    'verified clock. The window is a review policy, not a guarantee against state '
    'changes. No current state, future execution, gas, authority, ABI authenticity, '
    'provider identity or chain authenticity is established. Calls are independent '
    'and do not share simulated writes. No network request or transaction is made.'
)


def timestamp(value):
    number = core.quantity(value)
    core.require(number <= 2**63 - 1, 'timestamp exceeds supported Unix time range')
    return number


def policy(value):
    sets.bounded(value)
    core.require(isinstance(value, dict) and set(value) ==
                 {'schema', 'as_of', 'max_age_seconds', 'plan'},
                 'policy requires exactly schema, as_of, max_age_seconds and plan')
    core.require(value['schema'] == SCHEMA, 'unsupported set expiry schema')
    as_of = timestamp(value['as_of'])
    age = value['max_age_seconds']
    core.require(type(age) is int and 0 <= age <= MAX_AGE,
                 'max_age_seconds must be an integer from 0 through 2678400')
    plan = sets.plan(value['plan'])
    timestamp(plan['block']['timestamp'])
    return {'schema': SCHEMA, 'as_of': hex(as_of), 'max_age_seconds': age, 'plan': plan}


def evaluate(evidence, selected):
    chosen = policy(selected)
    result = sets.evaluate(evidence, chosen['plan'])
    observed = timestamp(chosen['plan']['block']['timestamp'])
    as_of = timestamp(chosen['as_of'])
    age = as_of - observed
    freshness = ('before_block' if age < 0 else
                 'within_window' if age <= chosen['max_age_seconds'] else 'expired')
    report = {
        'schema': SCHEMA, 'verdict': 'inconclusive', 'reason': '',
        'as_of': chosen['as_of'], 'max_age_seconds': chosen['max_age_seconds'],
        'block_timestamp': hex(observed), 'age_seconds': age,
        'expires_at': hex(observed + chosen['max_age_seconds']),
        'freshness': freshness, 'set_binding': result,
        'policy_sha256': sets.binding.digest(chosen), 'limits': LIMITS,
    }
    if result['verdict'] != 'bound':
        report.update(verdict=result['verdict'], reason='complete set binding is ' + result['verdict'])
    elif freshness == 'before_block':
        report['reason'] = 'declared review time precedes the reviewed block'
    elif freshness == 'expired':
        report.update(verdict='expired', reason='complete matching set is older than the declared age window')
    else:
        report.update(verdict='fresh', reason='complete matching set is within the declared age window')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo', help='replay the real historical ZTO-first set offline')
    check = commands.add_parser('check', help='check evidence against an explicit set expiry policy')
    check.add_argument('evidence')
    check.add_argument('policy')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            chosen = sets.binding.read_json(HERE / 'zto-set-expiry-policy.json')
            evidence = sets.binding.read_json(HERE.parent / 'rehearsal-set' / 'zto-set-evidence.json')
        else:
            chosen = sets.binding.read_json(args.policy)
            policy(chosen)
            evidence = sets.binding.read_json(args.evidence)
        report = evaluate(evidence, chosen)
        print(json.dumps(report, indent=2, allow_nan=False))
        return EXIT[report['verdict']]
    except (ValueError, KeyError, TypeError, OSError, RecursionError, core.RPCError) as exc:
        print(json.dumps({'schema': SCHEMA, 'verdict': 'inconclusive', 'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
