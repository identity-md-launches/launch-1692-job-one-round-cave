"""Real evidence replay and isolated scenario mutations; no network."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
import spender_exposure as tool


class SpenderTests(unittest.TestCase):
    def setUp(self):
        self.evidence = tool.gate.load(tool.exposure.DEFAULT)

    def test_real_inventory_partition(self):
        result = tool.assess(self.evidence)
        self.assertEqual(result['measured_pair_count'], 19)
        self.assertEqual(result['measured_owner_count'], 16)
        self.assertEqual(result['block']['block_number'], 26187572)
        self.assertEqual(sum(s['active_permission_count'] for s in result['spenders']), 3)
        self.assertEqual(sum(s['active_empty_balance_count'] for s in result['spenders']), 2)
        self.assertEqual(sum(s['measured_owner_count'] for s in result['spenders']), 19)
        self.assertFalse(result['complete_wallet_audit'])
        pairs = [(r['owner'], s['spender']) for s in result['spenders'] for r in s['owners']]
        self.assertEqual(len(pairs), len(set(pairs)))

    def test_distinct_owner_totals(self):
        result = tool.assess(self.evidence)
        for spender in result['spenders']:
            expected = sum(min(int(r['allowance_raw']), int(r['balance_raw'])) for r in spender['owners'])
            self.assertEqual(int(spender['measured_spendable_upper_bound_raw']), expected)

    def test_overlapping_spenders_not_combined(self):
        observed = copy.deepcopy(next(o for o in self.evidence['observations']
                                     if len(o['raw']['allowances']) >= 2))
        observed['raw']['balances'][0]['result'] = '0x' + format(4, '064x')
        for row in observed['raw']['allowances']:
            row['result'] = '0x' + format(6, '064x')
        result = tool.assess(observed)
        self.assertEqual(result['owner_capped_combined_upper_bound_raw'], '4')
        self.assertEqual(sum(int(s['measured_spendable_upper_bound_raw']) for s in result['spenders']),
                         4 * len(observed['raw']['allowances']))

    def test_explicit_receipt_on_empty_balance(self):
        receipts = tool.gate.load(tool.HERE.parent / 'receipt-exposure/hypothetical-one-zto.json')
        before, after = tool.assess(self.evidence), tool.assess(self.evidence, receipts)
        self.assertEqual(sum(int(s['incremental_exposure_raw']) for s in after['spenders']), 10**18)
        self.assertEqual(int(after['scenario_owner_capped_combined_upper_bound_raw'])
                         - int(before['owner_capped_combined_upper_bound_raw']), 10**18)
        self.assertNotEqual(before['input_sha256']['receipts'], after['input_sha256']['receipts'])

    def test_sorting_and_reordering(self):
        report = tool.assess(self.evidence)
        keys = [(-int(s['scenario_spendable_upper_bound_raw']), -s['active_permission_count'], s['spender'])
                for s in report['spenders']]
        self.assertEqual(keys, sorted(keys))
        reversed_evidence = copy.deepcopy(self.evidence)
        reversed_evidence['observations'].reverse()
        reversed_report = tool.assess(reversed_evidence)
        self.assertEqual(report['spenders'], reversed_report['spenders'])
        self.assertNotEqual(report['input_sha256']['observation'], reversed_report['input_sha256']['observation'])

    def test_inputs_unchanged(self):
        original = copy.deepcopy(self.evidence)
        tool.assess(self.evidence)
        self.assertEqual(original, self.evidence)

    def test_duplicate_pair_refused(self):
        self.evidence['observations'].append(copy.deepcopy(self.evidence['observations'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate inventory pair'):
            tool.assess(self.evidence)

    def test_incoherent_block_and_bad_abi_refused(self):
        changed = copy.deepcopy(self.evidence)
        changed['observations'][0]['block']['hash'] = changed['observations'][1]['block']['hash'][:-1] + '0'
        with self.assertRaises(ValueError):
            tool.assess(changed)
        changed = copy.deepcopy(self.evidence)
        changed['observations'][0]['raw']['allowances'][0]['result'] = '0x01'
        with self.assertRaises(ValueError):
            tool.assess(changed)

    def test_report_not_evidence(self):
        with self.assertRaises((ValueError, KeyError)):
            tool.assess(tool.assess(self.evidence))

    def test_cli_offline_and_path_guard(self):
        process = subprocess.run([sys.executable, '-B', str(Path(tool.__file__))], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)['spenders'], tool.assess(self.evidence)['spenders'])
        process = subprocess.run([sys.executable, '-B', str(Path(tool.__file__)), '--observation', '../outside.json'],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 1)
        self.assertIn('inside the current workspace', process.stderr)


if __name__ == '__main__':
    unittest.main()
