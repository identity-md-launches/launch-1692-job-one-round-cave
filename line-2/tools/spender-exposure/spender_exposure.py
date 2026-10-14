#!/usr/bin/env python3
"""Group historical ERC-20 permissions by spender, without double-counting owners."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'receipt-exposure'))
import receipt_exposure as exposure

gate = exposure.gate


def assess(observation, receipts=None):
    baseline = exposure.assess(observation, receipts)
    groups = {}
    for owner in baseline['owners']:
        for pair in owner['pairs']:
            groups.setdefault(pair['spender'], []).append({
                'owner': owner['owner'], 'balance_raw': owner['balance_raw'],
                'hypothetical_balance_raw': owner['hypothetical_balance_raw'],
                'allowance_raw': pair['allowance_raw'],
                'permission_active': pair['permission_active'],
                'max_uint256': int(pair['allowance_raw']) == gate.lens.MAX_UINT,
                'active_on_empty_balance': pair['permission_active'] and int(owner['balance_raw']) == 0,
                'measured_spendable_upper_bound_raw': pair['before_spendable_upper_bound_raw'],
                'scenario_spendable_upper_bound_raw': pair['after_spendable_upper_bound_raw'],
                'incremental_exposure_raw': pair['incremental_exposure_raw'],
            })
    spenders = []
    for spender, owners in groups.items():
        spenders.append({
            'spender': spender, 'measured_owner_count': len(owners),
            'active_permission_count': sum(row['permission_active'] for row in owners),
            'active_empty_balance_count': sum(row['active_on_empty_balance'] for row in owners),
            'max_uint256_permission_count': sum(row['max_uint256'] for row in owners),
            'measured_spendable_upper_bound_raw': str(sum(int(row['measured_spendable_upper_bound_raw']) for row in owners)),
            'scenario_spendable_upper_bound_raw': str(sum(int(row['scenario_spendable_upper_bound_raw']) for row in owners)),
            'incremental_exposure_raw': str(sum(int(row['incremental_exposure_raw']) for row in owners)),
            'owners': sorted(owners, key=lambda row: row['owner']),
        })
    spenders.sort(key=lambda row: (-int(row['scenario_spendable_upper_bound_raw']),
                                 -row['active_permission_count'], row['spender']))
    return {
        'schema': 'permission-spender-exposure-v1', 'mode': baseline['mode'],
        'chain_id': baseline['chain_id'], 'token': baseline['token'],
        'token_address': baseline['token_address'], 'decimals': baseline['decimals'],
        'block': baseline['block'], 'input_sha256': baseline['input_sha256'],
        'complete_wallet_audit': False, 'measured_pair_count': baseline['measured_pair_count'],
        'measured_owner_count': len(baseline['owners']), 'measured_spender_count': len(spenders),
        'owner_capped_combined_upper_bound_raw': str(sum(int(row['before_combined_spendable_upper_bound_raw']) for row in baseline['owners'])),
        'scenario_owner_capped_combined_upper_bound_raw': str(sum(int(row['after_combined_spendable_upper_bound_raw']) for row in baseline['owners'])),
        'spenders': spenders,
        'limitations': [
            'Historical trusted RPC evidence; no present-state, state-proof or future-execution claim.',
            'Each spender total sums distinct owners only; different spender totals overlap and must not be added.',
            'The combined bound caps each owner at its balance before summing distinct owners.',
            'Sorting is exposure arithmetic, not a maliciousness, trust or safety score.',
            'Empty balances retain active permissions; explicit receipts are hypothetical net increases.',
            'Only measured standard ERC-20 pairs: unknown spenders, Permit2, signatures and custom authorizations are omitted.',
            'No transaction, wallet, key, signing, sending, payment or environment access.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation', help='workspace raw permission evidence, ZTO first or IMD')
    parser.add_argument('--receipts', help='optional workspace explicit hypothetical net receipt scenario')
    args = parser.parse_args(argv)
    try:
        result = assess(gate.load(args.observation or exposure.DEFAULT),
                        None if args.receipts is None else gate.load(args.receipts))
        result['demonstration'] = args.observation is None
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
