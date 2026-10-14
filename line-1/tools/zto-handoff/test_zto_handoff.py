"""Offline tests for the bounded ZTO/IMD planning handoff."""
import contextlib
import copy
import io
import json
import unittest
from unittest.mock import patch

import zto_handoff as h


class HandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observation = h.review.read_json(h.review.DEFAULT_SNAPSHOT)
        cls.report = h.review.read_json(h.review.DEFAULT_REPORT)
        cls.policy = h.review.read_json(h.review.HERE / 'demo-policy.json')

    def test_real_evidence_makes_one_complete_zto_handoff(self):
        result = h.handoff(self.observation, self.report, self.policy, '100000000')
        self.assertEqual(result['status'], 'ready_for_human_review')
        self.assertEqual(result['requested_input_raw'], str(10**26))
        self.assertEqual(result['minimum_output_raw'], '1184169088029408336486')
        self.assertEqual(result['settlement'], 'unspecified')
        self.assertIsNone(result['transaction'])
        self.assertEqual(result['handoff_sha256'], h.review.digest(
            {key: value for key, value in result.items() if key != 'handoff_sha256'}))
        self.assertEqual(h.verify_handoff(result)['status'], 'accepted')

    def test_verifier_refuses_tampering_and_settlement_fields(self):
        result = h.handoff(self.observation, self.report, self.policy, '100000000')
        changed = copy.deepcopy(result)
        changed['minimum_output_raw'] = '1'
        with self.assertRaisesRegex(ValueError, 'display disagrees'):
            h.verify_handoff(changed)
        changed = copy.deepcopy(result)
        changed['transaction'] = {'to': 'anything'}
        with self.assertRaisesRegex(ValueError, 'settlement'):
            h.verify_handoff(changed)
        changed = copy.deepcopy(result)
        changed['handoff_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            h.verify_handoff(changed)

    def redigest(self, value):
        value['handoff_sha256'] = h.review.digest(
            {key: item for key, item in value.items() if key != 'handoff_sha256'})

    def test_redigested_invalid_chain_ids_are_refused(self):
        for chain_id in (True, 1.0, '1', 2):
            with self.subTest(chain_id=chain_id):
                changed = h.handoff(self.observation, self.report, self.policy, '100000000')
                changed['chain_id'] = chain_id
                self.redigest(changed)
                with self.assertRaisesRegex(ValueError, 'assigned Ethereum'):
                    h.verify_handoff(changed)

    def test_redigested_invalid_block_encodings_and_widths_are_refused(self):
        invalid = [
            ('hash', '0x1'), ('hash', '0x' + 'a' * 63),
            ('hash', '0x' + 'a' * 65), ('hash', '0x' + 'A' * 64),
            ('hash', None), ('number', '0x018f8a44'), ('number', '0x18F8A44'),
            ('number', '0x' + '1' * 17), ('number', '0x0'),
            ('number', hex(h.review.sizes.path.z.INIT_BLOCK - 1)),
            ('number', 26184260), ('timestamp', '0x00'), ('timestamp', '0x0'),
            ('timestamp', '0x' + '1' * 17), ('timestamp', True),
        ]
        for key, value in invalid:
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(h.handoff(
                    self.observation, self.report, self.policy, '100000000'))
                changed['block'][key] = value
                self.redigest(changed)
                with self.assertRaisesRegex(ValueError, 'invalid pinned block'):
                    h.verify_handoff(changed)

    def test_redigested_inconsistent_age_is_refused(self):
        original = h.handoff(self.observation, self.report, self.policy, '100000000')
        number = int(original['block']['number'], 16)
        for reference, age in ((1, 0), (number - 1, 0), (number, 1),
                               (number + 10, 9), (number + 10, 11)):
            with self.subTest(reference=reference, age=age):
                changed = copy.deepcopy(original)
                changed['review_reference_block'] = reference
                changed['review_age_blocks'] = age
                self.redigest(changed)
                with self.assertRaisesRegex(ValueError, 'review age disagrees'):
                    h.verify_handoff(changed)

    def test_redigested_invalid_review_integer_ranges_are_refused(self):
        for key in ('review_reference_block', 'review_age_blocks'):
            for value in (True, -1, 1 << 64, 1.0, '1'):
                with self.subTest(key=key, value=value):
                    changed = h.handoff(self.observation, self.report, self.policy, '100000000')
                    changed[key] = value
                    self.redigest(changed)
                    with self.assertRaisesRegex(ValueError, 'invalid review settings'):
                        h.verify_handoff(changed)

    def test_redigested_amounts_outside_pool_delta_are_refused(self):
        for prefix in ('requested_input', 'minimum_output'):
            for raw in (1 << 127, 1 << 128):
                with self.subTest(prefix=prefix, raw=raw):
                    changed = h.handoff(self.observation, self.report, self.policy, '100000000')
                    changed[prefix + '_raw'] = str(raw)
                    changed[prefix] = h.review.sizes.path.z.units(raw, 18)
                    self.redigest(changed)
                    with self.assertRaisesRegex(ValueError, 'positive int128 pool delta'):
                        h.verify_handoff(changed)

    def test_structural_verifier_accepts_valid_width_and_age_boundaries(self):
        # This remains a structural check, not evidence authentication. These
        # boundary edits are intentionally not submitted to verify_evidence.
        changed = copy.deepcopy(h.handoff(
            self.observation, self.report, self.policy, '100000000'))
        changed['review_reference_block'] = (1 << 64) - 1
        changed['review_age_blocks'] = ((1 << 64) - 1) - int(changed['block']['number'], 16)
        changed['block']['timestamp'] = hex((1 << 64) - 1)
        for prefix in ('requested_input', 'minimum_output'):
            changed[prefix + '_raw'] = str((1 << 127) - 1)
            changed[prefix] = h.review.sizes.path.z.units((1 << 127) - 1, 18)
        self.redigest(changed)
        self.assertEqual(h.verify_handoff(changed)['status'], 'accepted')
        changed['block']['number'] = hex((1 << 64) - 1)
        changed['review_age_blocks'] = 0
        self.redigest(changed)
        self.assertEqual(h.verify_handoff(changed)['status'], 'accepted')

    def test_unreviewed_or_partial_amount_refused(self):
        for amount in ('1000000000', '2'):
            with self.assertRaises(ValueError):
                h.handoff(self.observation, self.report, self.policy, amount)

    def test_review_mismatch_is_not_handed_off(self):
        changed = copy.deepcopy(self.report)
        changed['candidates'][1]['minimum_output_raw'] = '1'
        with self.assertRaisesRegex(ValueError, 'review did not accept'):
            h.handoff(self.observation, changed, self.policy, '100000000')

    def test_cli_is_offline_and_uses_exact_decimal(self):
        with patch.object(h.review.sizes.path.z, 'RPC', side_effect=AssertionError('network forbidden')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(h.main(['--demo', '--amount', '100000000']), 0)
        self.assertEqual(json.loads(output.getvalue())['input_token'], 'ZTO')
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(h.main(['--demo', '--amount', '3']), 1)
        self.assertIn('error', json.loads(error.getvalue()))

    def test_verify_cli_uses_workspace_json_reader(self):
        result = h.handoff(self.observation, self.report, self.policy, '100000000', 'historical_demo')
        with patch.object(h.review, 'read_json', return_value=result) as read_json:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(h.main(['--verify', 'line-1/tools/zto-handoff/example.json']), 0)
        self.assertEqual(read_json.call_count, 1)
        self.assertEqual(json.loads(output.getvalue())['status'], 'accepted')

    def test_evidence_verifier_rebuilds_the_handoff(self):
        result = h.handoff(self.observation, self.report, self.policy, '100000000', 'historical_demo')
        accepted = h.verify_evidence(result, self.observation, self.report, self.policy)
        self.assertEqual(accepted['status'], 'accepted')
        changed = copy.deepcopy(result)
        changed['limitations'][0] = 'A different claim.'
        changed['handoff_sha256'] = h.review.digest(
            {key: value for key, value in changed.items() if key != 'handoff_sha256'})
        with self.assertRaisesRegex(ValueError, 'exactly match'):
            h.verify_evidence(changed, self.observation, self.report, self.policy)

    def test_evidence_cli_is_offline_and_requires_complete_inputs(self):
        with patch.object(h.review.sizes.path.z, 'RPC', side_effect=AssertionError('network forbidden')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(h.main(['--demo', '--verify-evidence',
                                         str(h.HERE / 'demo-handoff.json')]), 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'accepted')
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(h.main(['--verify-evidence', str(h.HERE / 'demo-handoff.json')]), 1)
        self.assertIn('error', json.loads(error.getvalue()))

    def test_cli_can_save_only_a_newly_reviewed_handoff(self):
        with patch.object(h.review.sizes.path, 'save_json') as save_json:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(h.main(['--demo', '--amount', '100000000',
                                         '--save', 'test/scratch/handoff.json']), 0)
        saved_path, saved_value = save_json.call_args.args
        self.assertEqual(saved_path, 'test/scratch/handoff.json')
        self.assertEqual(saved_value['status'], 'ready_for_human_review')
        self.assertEqual(json.loads(output.getvalue())['handoff_sha256'],
                         saved_value['handoff_sha256'])

    def test_cli_refuses_save_on_a_verification_result(self):
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(h.main(['--verify', str(h.HERE / 'demo-handoff.json'),
                                     '--save', 'test/scratch/verification.json']), 1)
        self.assertIn('--save is available only', json.loads(error.getvalue())['error'])


if __name__ == '__main__':
    unittest.main()
