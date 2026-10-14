"""Real evidence integration and failure gates; no new or fabricated chain evidence."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fresh_surface as tool


class FreshSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.saved, self.policy, self.choices, self.proofs = tool.demo_inputs()
        self.time = int(self.policy['plan']['block']['timestamp'], 16)
        self.label = self.policy['plan']['calls'][0]['id']

    def run_check(self):
        return tool.evaluate(self.saved, self.policy, self.choices, self.proofs)

    def test_real_bound_proof_decoded_return(self):
        before = copy.deepcopy((self.saved, self.policy, self.choices, self.proofs))
        report = self.run_check()
        self.assertEqual(report['verdict'], 'aligned')
        self.assertEqual(report['expiry']['verdict'], 'fresh')
        self.assertEqual(report['decoded_calls'][0]['returns'][0]['value'],
                         '285939607966355541747129965')
        self.assertNotIn('decoded_calls', report['surface_context'])
        self.assertEqual(before, (self.saved, self.policy, self.choices, self.proofs))

    def test_inclusive_expiry_and_next_second(self):
        for age, expected in ((0, 'aligned'), (7200, 'aligned'), (7201, 'withheld')):
            self.policy['as_of'] = hex(self.time + age)
            result = self.run_check()
            self.assertEqual(result['verdict'], expected)
            if age == 7201:
                self.assertIsNone(result['decoded_calls'])
                self.assertIsNone(result['surface_context'])

    def test_stale_skips_expensive_proof_join(self):
        self.policy['as_of'] = hex(self.time + 7201)
        with patch.object(tool.surface, 'evaluate', side_effect=AssertionError('must skip')):
            self.assertEqual(self.run_check()['expiry']['verdict'], 'expired')

    def test_before_block_skips_join(self):
        self.policy['as_of'] = hex(self.time - 1)
        result = self.run_check()
        self.assertEqual(result['expiry']['verdict'], 'inconclusive')
        self.assertIsNone(result['decoded_calls'])

    def test_fresh_but_changed_return_withholds(self):
        self.policy['plan']['calls'][0]['expected_return'] = '0x'
        result = self.run_check()
        self.assertEqual(result['expiry']['verdict'], 'mismatch')
        self.assertIsNone(result['decoded_calls'])
        self.assertIsNone(result['surface_context'])

    def test_matching_relabelled_block_does_not_relabel_proof(self):
        number = hex(int(self.policy['plan']['block']['number'], 16) + 1)
        self.policy['plan']['block']['number'] = number
        self.saved['observations'][0]['observation']['block']['number'] = number
        result = self.run_check()
        self.assertEqual(result['expiry']['verdict'], 'fresh')
        self.assertEqual(result['verdict'], 'withheld')
        self.assertIsNone(result['decoded_calls'])
        self.assertIn('same_block_number', result['surface_context']['code_checks'][0]['failed_checks'])

    def test_corrupt_proof_never_releases(self):
        self.proofs[self.label]['header_rlp'] = '0x00'
        with self.assertRaises(ValueError):
            self.run_check()

    def test_anchor_validity_and_wrong_anchor(self):
        with self.assertRaises(ValueError):
            tool.evaluate(self.saved, self.policy, self.choices, self.proofs, 'bad')
        real_hash = self.policy['plan']['block']['hash']
        report = tool.evaluate(self.saved, self.policy, self.choices, self.proofs, real_hash)
        self.assertEqual(report['verdict'], 'aligned')
        wrong_hash = '0x' + ('01' if real_hash[2:4] != '01' else '02') + real_hash[4:]
        with self.assertRaises(ValueError):
            tool.evaluate(self.saved, self.policy, self.choices, self.proofs, wrong_hash)

    def test_coverage_and_unknown_choice_fields_even_when_stale(self):
        self.policy['as_of'] = hex(self.time + 7201)
        with self.assertRaises(ValueError):
            tool.evaluate(self.saved, self.policy, {}, self.proofs)
        with self.assertRaises(ValueError):
            tool.evaluate(self.saved, self.policy, self.choices, {})
        self.choices[self.label]['gas'] = '0x5208'
        with self.assertRaises(ValueError):
            self.run_check()

    def test_real_three_calls_missing_member_withholds(self):
        read = tool.expiry.sets.binding.read_json
        self.saved = read(tool.HERE.parent / 'rehearsal-set/zto-set-evidence.json')
        self.policy = read(tool.HERE / 'zto-set-expiry-policy.json')
        self.choices = {entry['id']: self.choices[self.label] for entry in self.policy['plan']['calls']}
        self.proofs = {entry['id']: self.proofs[self.label] for entry in self.policy['plan']['calls']}
        self.saved['observations'].pop()
        result = self.run_check()
        self.assertEqual(result['expiry']['verdict'], 'inconclusive')
        self.assertIsNone(result['decoded_calls'])

    def test_digest_binds_policy_choices_proofs(self):
        self.policy['as_of'] = hex(self.time + 7201)
        first = self.run_check()['input_sha256']
        self.policy['max_age_seconds'] = 7199
        self.assertNotEqual(first['policy'], self.run_check()['input_sha256']['policy'])
        self.choices[self.label]['signature'] = 'totalSupply()'
        self.assertNotEqual(first['choices'], self.run_check()['input_sha256']['choices'])
        self.proofs[self.label]['header_rlp'] = '0x00'
        self.assertNotEqual(first['proofs'], self.run_check()['input_sha256']['proofs'])

    def test_cli_demos_without_network(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            for command, code, verdict in (('demo', 0, 'aligned'), ('expired-demo', 2, 'withheld')):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(tool.main([command]), code)
                self.assertEqual(json.loads(output.getvalue())['verdict'], verdict)

    def test_explicit_cli_and_strict_input_rejection(self):
        scratch = Path('test/scratch'); scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            folder = Path(folder)
            manifest = {'schema': 'set-surface-manifest-v1', 'members': [{
                'id': self.label, 'signature': 'balanceOf(address)', 'return_types': ['uint256'],
                'proof': 'shared/surface-return/zto-proof.json'}]}
            values = [('evidence', self.saved), ('policy', self.policy), ('manifest', manifest)]
            paths = []
            for name, value in values:
                path = folder / (name + '.json'); path.write_text(json.dumps(value)); paths.append(str(path))
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(tool.main(['check'] + paths), 0)
            self.assertEqual(json.loads(output.getvalue())['verdict'], 'aligned')
            (folder / 'policy.json').write_text('{"schema":"a","schema":"b"}')
            with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(tool.main(['check'] + paths), 1)
            self.assertEqual(output.getvalue(), '')
        with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(tool.main(['check', '../outside.json', 'missing.json', 'missing.json']), 1)
        self.assertEqual(output.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
