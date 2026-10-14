#!/usr/bin/env python3
"""Recompute two ZTO/IMD snapshots without silently lowering an earlier minimum."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'zto-review'))
import zto_review as review

HERE = Path(__file__).resolve().parent
BEFORE = HERE.parent / 'zto-path' / 'observation.json'
AFTER = HERE.parent / 'zto-refresh' / 'live-observation.json'
DEMO_REFERENCE = 26186365


def uint64(value, label):
    review.sizes.path.z.require(type(value) is int and 0 <= value < 1 << 64,
                                label + ' must be a nonnegative uint64 integer')
    return value


def block_context(observation):
    """Use strict header forms for ordering; ancestor decoder validates pool state."""
    require = review.sizes.path.z.require
    block = observation['base']['block']
    for field in ('number', 'timestamp'):
        value = block[field]
        require(type(value) is str and re.fullmatch('0x[0-9a-fA-F]+', value) is not None,
                'block ' + field + ' must be hex text')
        uint64(int(value, 16), 'block ' + field)
    require(type(block['hash']) is str and
            re.fullmatch('0x[0-9a-fA-F]{64}', block['hash']) is not None,
            'block hash must be bytes32 hex text')
    source = observation['base']['source']
    require(type(source) is str and 0 < len(source) <= 2048, 'source must be short text')
    return {'snapshot_sha256': review.digest(observation), 'block': block,
            'block_number': int(block['number'], 16), 'source': source}


def rational(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator),
            'ceiling': review.sizes.ceiling(value)}


def compare(before, after, amounts, token, slippage_bps, max_deterioration_bps,
            reference_block, max_age_blocks):
    """Each size is independent. Only original minima may be carried forward.

    Source labels, hashes and block order are descriptive checks, not consensus
    or provider proofs. The explicit reference height is a caller trust input.
    """
    sizes = review.sizes
    require = sizes.path.z.require
    sizes.bps(slippage_bps, 'slippage bps')
    sizes.bps(max_deterioration_bps, 'maximum deterioration bps')
    uint64(reference_block, 'reference block')
    uint64(max_age_blocks, 'maximum age blocks')
    require(token in ('ZTO', 'IMD'), 'input must be ZTO or IMD')
    old_state, _, _ = sizes.path.decode(before)
    new_state, _, _ = sizes.path.decode(after)
    require(old_state['decimals'] == new_state['decimals'],
            'token decimals changed between observations')
    old_context, new_context = block_context(before), block_context(after)
    # Validate every amount, including when age/order controls will refuse.
    require(type(amounts) is list and 1 <= len(amounts) <= sizes.MAX_CANDIDATES and
            all(type(a) is str and len(a) <= 100 for a in amounts),
            'amounts must be 1..20 short decimal strings')
    din = old_state['decimals'][1 if token == 'ZTO' else 0]
    dout = old_state['decimals'][0 if token == 'ZTO' else 1]
    for amount in amounts:
        require(sizes.path.z.parse_amount(amount, din) < 1 << 127,
                'input must fit positive int128 pool delta')
    old_number, new_number = old_context['block_number'], new_context['block_number']
    age = reference_block - new_number
    reasons = []
    if new_number <= old_number:
        reasons.append('later_block_not_strictly_newer')
    if before['base']['block']['hash'].lower() == after['base']['block']['hash'].lower():
        reasons.append('same_block_hash')
    if int(after['base']['block']['timestamp'], 16) <= int(before['base']['block']['timestamp'], 16):
        reasons.append('later_timestamp_not_strictly_newer')
    if age < 0:
        reasons.append('later_snapshot_after_reference')
    elif age > max_age_blocks:
        reasons.append('later_snapshot_too_old')
    result = {'schema': 'zto-drift-report-v1', 'status': 'refuse',
              'chain_id': 1, 'pool_id': sizes.path.z.POOL,
              'before': old_context, 'after': new_context,
              'block_gap': new_number - old_number,
              'reference_block': reference_block, 'later_age_blocks': age,
              'max_age_blocks': max_age_blocks, 'input_token': token,
              'output_token': 'IMD' if token == 'ZTO' else 'ZTO',
              'amounts': list(amounts), 'slippage_bps': slippage_bps,
              'max_deterioration_bps': max_deterioration_bps,
              'reasons': reasons, 'candidates': [], 'covered_count': 0,
              'carried_bounds': [],
              'minimum_rule': 'floor(before_output_raw * (10000 - slippage_bps) / 10000)',
              'deterioration_rule': '(before_output_raw - after_output_raw) * 10000 / before_output_raw',
              'limitations': [
                  'Both snapshots are historical RPC evidence, not state proofs or current quotes.',
                  'Strict block order does not prove chain ancestry, consensus or provider authenticity.',
                  'Reference height and tolerance are caller inputs; age is not a live freshness check.',
                  'Each amount is an independent quote; observations do not model intervening or successive trades.',
                  'Only the original minimum is carried; later output does not renew slippage tolerance.',
                  'Bounds are planning numbers, not receipt guarantees or executable transactions.',
                  'Reuses ZTO Sizes/Path arithmetic; no independent math, settlement, transfers, gas or MEV simulation.']}
    if reasons:
        return result
    old_report = sizes.compare_sizes(before, amounts, token, slippage_bps)
    new_report = sizes.compare_sizes(after, amounts, token, slippage_bps)
    for index, (old, new) in enumerate(zip(old_report['candidates'], new_report['candidates'])):
        row = {'index': index, 'amount': amounts[index],
               'requested_input_raw': old['requested_input_raw'],
               'before_pool_status': old['pool_status'], 'after_pool_status': new['pool_status'],
               'before_ticks_crossed': old['initialized_ticks_crossed'],
               'after_ticks_crossed': new['initialized_ticks_crossed'],
               'status': 'refuse', 'reasons': []}
        # An incomplete output is never turned into a bound or drift statistic.
        if old['status'] == 'incomplete':
            row['reasons'].append('before_incomplete')
        if new['status'] == 'incomplete':
            row['reasons'].append('after_incomplete')
        if row['reasons']:
            result['candidates'].append(row)
            continue
        old_output = int(old['estimate']['output_raw'])
        new_output = int(new['estimate']['output_raw'])
        minimum = old_output * (10000 - slippage_bps) // 10000
        row.update(before_output_raw=str(old_output), after_output_raw=str(new_output),
                   before_output=sizes.path.z.units(old_output, dout),
                   after_output=sizes.path.z.units(new_output, dout),
                   output_change_raw=str(new_output - old_output))
        if minimum == 0:
            row['reasons'].append('zero_original_minimum')
        else:
            loss = Fraction((old_output - new_output) * 10000, old_output)
            row.update(original_minimum_output_raw=str(minimum),
                       original_minimum_output=sizes.path.z.units(minimum, dout),
                       deterioration_bps=rational(loss),
                       later_headroom_raw=str(new_output - minimum),
                       original_minimum_covered=new_output >= minimum)
            if new_output < minimum:
                row['reasons'].append('original_minimum_breached')
            if loss > max_deterioration_bps:
                row['reasons'].append('deterioration_limit_exceeded')
            if not row['reasons']:
                row['status'] = 'covered_at_later_snapshot'
                result['carried_bounds'].append({
                    'candidate_index': index, 'input_token': token,
                    'output_token': result['output_token'],
                    'requested_input_raw': row['requested_input_raw'],
                    'minimum_output_raw': str(minimum),
                    'later_estimated_output_raw': str(new_output)})
        result['candidates'].append(row)
    result['covered_count'] = len(result['carried_bounds'])
    if result['covered_count']:
        result['status'] = 'compared'
    else:
        reasons.append('no_original_minimum_carried')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true', help='offline real historical ZTO comparison')
    parser.add_argument('--before', help='workspace earlier ZTO Path snapshot JSON')
    parser.add_argument('--after', help='workspace later ZTO Path snapshot JSON')
    parser.add_argument('--input', choices=('ZTO', 'IMD'))
    parser.add_argument('--amount', action='append', help='repeat for 1..20 independent amounts')
    parser.add_argument('--slippage-bps', type=int)
    parser.add_argument('--max-deterioration-bps', type=int)
    parser.add_argument('--reference-block', type=int)
    parser.add_argument('--max-age-blocks', type=int)
    args = parser.parse_args(argv)
    try:
        custom = [args.before, args.after, args.input, args.amount, args.slippage_bps,
                  args.max_deterioration_bps, args.reference_block, args.max_age_blocks]
        if args.demo:
            if any(value is not None for value in custom):
                raise ValueError('--demo cannot be combined with custom arguments')
            before, after = review.read_json(BEFORE), review.read_json(AFTER)
            result = compare(before, after, ['1', '100000000', '1000000000'], 'ZTO',
                             100, 100, DEMO_REFERENCE, 0)
        else:
            required = (args.before, args.after, args.amount, args.slippage_bps,
                        args.max_deterioration_bps, args.reference_block, args.max_age_blocks)
            if any(value is None for value in required):
                raise ValueError('supply --before, --after, --amount, --slippage-bps, '
                                 '--max-deterioration-bps, --reference-block and --max-age-blocks')
            result = compare(review.read_json(args.before), review.read_json(args.after),
                             args.amount, args.input or 'ZTO', args.slippage_bps,
                             args.max_deterioration_bps, args.reference_block, args.max_age_blocks)
        result['mode'] = 'historical_demo' if args.demo else 'caller_inputs'
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result['status'] == 'compared' else 2
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError,
            RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
