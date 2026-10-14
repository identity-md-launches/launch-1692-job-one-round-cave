"""Real evidence replay and synthetic refusal cases; no network use."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import set_expiry as tool


class SetExpiryTests(unittest.TestCase):
    def setUp(self):
        self.policy = tool.sets.binding.read_json(tool.HERE / 'zto-set-expiry-policy.json')
        self.saved = tool.sets.binding.read_json(tool.HERE.parent / 'rehearsal-set' / 'zto-set-evidence.json')
        self.block_time = int(self.policy['plan']['block']['timestamp'], 16)

    def run_check(self):
        return tool.evaluate(self.saved, self.policy)

    def test_real_set(self):
        report = self.run_check()
        self.assertEqual(report['verdict'], 'fresh')
        self.assertEqual(report['age_seconds'], 3600)
        self.assertEqual(report['set_binding']['matched_count'], 3)
        self.assertEqual(report['expires_at'], hex(self.block_time + 7200))

    def test_expiry_boundary_inclusive(self):
        for age, verdict in ((0, 'fresh'), (7199, 'fresh'), (7200, 'fresh'), (7201, 'expired')):
            with self.subTest(age=age):
                self.policy['as_of'] = hex(self.block_time + age)
                self.assertEqual(self.run_check()['verdict'], verdict)

    def test_zero_window(self):
        self.policy['max_age_seconds'] = 0
        self.policy['as_of'] = hex(self.block_time)
        self.assertEqual(self.run_check()['verdict'], 'fresh')
        self.policy['as_of'] = hex(self.block_time + 1)
        self.assertEqual(self.run_check()['verdict'], 'expired')

    def test_future_block(self):
        self.policy['as_of'] = hex(self.block_time - 1)
        report = self.run_check()
        self.assertEqual(report['verdict'], 'inconclusive')
        self.assertEqual(report['freshness'], 'before_block')
        self.assertEqual(report['age_seconds'], -1)

    def test_missing_call_even_when_expired(self):
        self.saved['observations'].pop()
        self.policy['as_of'] = hex(self.block_time + 7201)
        report = self.run_check()
        self.assertEqual(report['verdict'], 'inconclusive')
        self.assertEqual(report['freshness'], 'expired')

    def test_mismatch_even_when_fresh_or_expired(self):
        self.saved['observations'][0]['observation']['outcome']['result'] = '0x' + '00' * 32
        for age in (3600, 7201):
            self.policy['as_of'] = hex(self.block_time + age)
            self.assertEqual(self.run_check()['verdict'], 'mismatch')

    def test_missing_sender_does_not_pass_freshness(self):
        del self.saved['observations'][0]['observation']['call']['from']
        self.assertEqual(self.run_check()['verdict'], 'inconclusive')

    def test_wrong_block_cannot_use_plan_timestamp(self):
        self.saved['observations'][1]['observation']['block']['timestamp'] = hex(self.block_time + 1)
        self.assertEqual(self.run_check()['verdict'], 'mismatch')

    def test_revert(self):
        self.saved['observations'][0]['observation']['outcome'] = {
            'error': {'code': 3, 'message': 'execution reverted', 'data': '0x'}}
        self.assertEqual(self.run_check()['verdict'], 'mismatch')

    def test_unexpected_and_duplicate_entries(self):
        extra = copy.deepcopy(self.saved['observations'][0])
        extra['id'] = 'extra'
        self.saved['observations'].append(extra)
        self.assertEqual(self.run_check()['verdict'], 'mismatch')
        extra['id'] = self.saved['observations'][0]['id']
        with self.assertRaisesRegex(ValueError, 'duplicate id'):
            self.run_check()

    def test_age_limits(self):
        for value in (-1, True, '7200', 1.5, None, tool.MAX_AGE + 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.policy['max_age_seconds'] = value
                self.run_check()
        self.policy['max_age_seconds'] = tool.MAX_AGE
        self.assertEqual(self.run_check()['verdict'], 'fresh')

    def test_timestamps_are_canonical_bounded_quantities(self):
        for value in ('0x00', -1, True, '123', '0x8000000000000000'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.policy['as_of'] = value
                self.run_check()

    def test_uppercase_hex_is_normalized(self):
        self.policy['as_of'] = '0xABC'
        self.assertEqual(tool.policy(self.policy)['as_of'], '0xabc')

    def test_block_timestamp_range(self):
        self.policy['plan']['block']['timestamp'] = '0x8000000000000000'
        with self.assertRaisesRegex(ValueError, 'Unix time range'):
            self.run_check()

    def test_strict_policy_fields_schema_and_size(self):
        self.policy['clock'] = 'trusted'
        with self.assertRaises(ValueError):
            self.run_check()
        del self.policy['clock']
        self.policy['schema'] = 'other'
        with self.assertRaises(ValueError):
            self.run_check()
        self.policy['padding'] = 'x' * 95000
        with self.assertRaisesRegex(ValueError, '95 KB'):
            self.run_check()

    def test_hash_binds_review_time_window_and_plan(self):
        initial = self.run_check()['policy_sha256']
        for field, value in (('as_of', hex(self.block_time + 3601)), ('max_age_seconds', 7201)):
            with self.subTest(field=field):
                chosen = copy.deepcopy(self.policy)
                chosen[field] = value
                self.assertNotEqual(tool.evaluate(self.saved, chosen)['policy_sha256'], initial)

    def test_inputs_unchanged_and_order_independent(self):
        before = copy.deepcopy((self.saved, self.policy))
        self.run_check()
        self.assertEqual((self.saved, self.policy), before)
        self.saved['observations'].reverse()
        self.policy['plan']['calls'].reverse()
        self.assertEqual(self.run_check()['verdict'], 'fresh')

    def test_demo_without_network_or_clock(self):
        with patch.object(tool.core.RPC, 'call', side_effect=AssertionError('network forbidden')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(tool.main(['demo']), 0)
        self.assertEqual(json.loads(output.getvalue())['verdict'], 'fresh')

    def test_real_cli_check_and_expired_exit(self):
        # Scratch inputs stay in the allowed disposable test directory.
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            p = Path(temp) / 'policy.json'
            e = Path(temp) / 'evidence.json'
            e.write_text(json.dumps(self.saved))
            for age, code, verdict in ((3600, 0, 'fresh'), (7201, 1, 'expired'), (-1, 2, 'inconclusive')):
                self.policy['as_of'] = hex(self.block_time + age)
                p.write_text(json.dumps(self.policy))
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(tool.main(['check', str(e), str(p)]), code)
                self.assertEqual(json.loads(output.getvalue())['verdict'], verdict)

    def test_parser_refuses_duplicate_keys_nonfinite_and_external_paths(self):
        for raw in (b'{"as_of":1,"as_of":2}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                tool.sets.binding.parse_json(raw)
        with self.assertRaises(ValueError):
            tool.sets.binding.read_json(Path.cwd().parent / 'outside.json')

    def test_cli_invalid_input(self):
        with patch.object(tool.sets.binding, 'read_json', side_effect=ValueError('invalid input')):
            with contextlib.redirect_stderr(io.StringIO()) as output:
                self.assertEqual(tool.main(['demo']), 2)
        self.assertEqual(json.loads(output.getvalue())['verdict'], 'inconclusive')


if __name__ == '__main__':
    unittest.main()
