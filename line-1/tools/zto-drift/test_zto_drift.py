"""Regression tests over saved real pool evidence and explicitly damaged copies."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from fractions import Fraction
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import zto_drift as drift


class DriftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = drift.review.read_json(drift.BEFORE)
        cls.after = drift.review.read_json(drift.AFTER)

    def compare(self, **changes):
        args = dict(before=self.before, after=self.after, amounts=['1'], token='ZTO',
                    slippage_bps=100, max_deterioration_bps=100,
                    reference_block=drift.DEMO_REFERENCE, max_age_blocks=0)
        args.update(changes)
        return drift.compare(**args)

    def test_real_zto_outputs_match_both_raw_quoter_returns(self):
        row = self.compare()['candidates'][0]
        sources = [('before', drift.HERE.parent / 'zto-path' / 'quoter-check.json'),
                   ('after', drift.HERE.parent / 'zto-refresh' / 'live-quoter-check.json')]
        for prefix, filename in sources:
            check = drift.review.read_json(filename)
            case = next(r for r in check['results'] if r['input_token'] == 'ZTO' and r['amount'] == '1')
            output = drift.review.sizes.path.z.words(case['raw_result'], 2)[0]
            self.assertEqual(int(row[prefix + '_output_raw']), output)
        self.assertEqual(row['status'], 'covered_at_later_snapshot')
        self.assertEqual(row['original_minimum_output_raw'], '15139234039518')
        self.assertLess(int(row['deterioration_bps']['numerator']), 0)

    def test_original_minimum_is_never_renewed(self):
        result = self.compare(amounts=['100000000'])
        row = result['candidates'][0]
        minimum = int(result['carried_bounds'][0]['minimum_output_raw'])
        self.assertEqual(minimum, 1184169088029408336486)
        self.assertNotEqual(minimum, int(row['after_output_raw']) * 9900 // 10000)
        self.assertLessEqual(minimum * 10000, int(row['before_output_raw']) * 9900)
        self.assertGreater((minimum + 1) * 10000, int(row['before_output_raw']) * 9900)

    def test_real_reverse_direction_breaches_old_minimum(self):
        result = self.compare(token='IMD')
        row = result['candidates'][0]
        self.assertEqual(row['before_output_raw'], '63756931927028793174084')
        self.assertEqual(row['after_output_raw'], '43324195593173213142556')
        self.assertEqual(row['original_minimum_output_raw'], '63119362607758505242343')
        self.assertFalse(row['original_minimum_covered'])
        self.assertIn('original_minimum_breached', row['reasons'])
        self.assertIn('deterioration_limit_exceeded', row['reasons'])
        self.assertEqual(result['carried_bounds'], [])
        self.assertEqual(result['status'], 'refuse')

    def test_exact_deterioration_filter_uses_fraction(self):
        result = self.compare(token='IMD', slippage_bps=9999, max_deterioration_bps=9999)
        ratio = result['candidates'][0]['deterioration_bps']
        loss = Fraction(int(ratio['numerator']), int(ratio['denominator']))
        self.assertNotEqual(loss.denominator, 1)
        floor = loss.numerator // loss.denominator
        refused = self.compare(token='IMD', slippage_bps=9999, max_deterioration_bps=floor)
        accepted = self.compare(token='IMD', slippage_bps=9999, max_deterioration_bps=floor + 1)
        self.assertEqual(refused['carried_bounds'], [])
        self.assertTrue(refused['candidates'][0]['original_minimum_covered'])
        self.assertEqual(accepted['covered_count'], 1)

    @staticmethod
    def narrow(snapshot):
        """Remove known outer coverage, without inventing any pool responses."""
        result = deepcopy(snapshot)
        state, _, _ = drift.review.sizes.path.decode(result)
        center = str(state['tick'] // state['spacing'] // 256)
        result['word_radius'] = 0
        result['bitmap'] = {center: result['bitmap'][center]}
        tick_keys = drift.review.sizes.path.tick_keys(
            {int(center): int(result['bitmap'][center], 16)}, state['spacing'])
        result['ticks'] = {k: v for k, v in result['ticks'].items() if int(k) in tick_keys}
        return result

    def test_complete_to_incomplete_withholds_every_bound(self):
        result = self.compare(after=self.narrow(self.after), amounts=['100000000'])
        row = result['candidates'][0]
        self.assertEqual(row['before_pool_status'], 'estimated')
        self.assertEqual(row['reasons'], ['after_incomplete'])
        self.assertNotIn('deterioration_bps', row)
        self.assertNotIn('original_minimum_output_raw', row)
        self.assertEqual(result['carried_bounds'], [])

    def test_incomplete_to_complete_is_not_an_original_bound(self):
        result = self.compare(before=self.narrow(self.before), token='IMD', amounts=['1000'])
        row = result['candidates'][0]
        self.assertEqual(row['after_pool_status'], 'estimated')
        self.assertEqual(row['reasons'], ['before_incomplete'])
        self.assertEqual(result['carried_bounds'], [])

    def test_zero_output_never_divides_or_releases(self):
        result = self.compare(amounts=['0.000000000000000001'])
        row = result['candidates'][0]
        self.assertEqual(row['reasons'], ['zero_original_minimum'])
        self.assertNotIn('deterioration_bps', row)
        self.assertEqual(result['carried_bounds'], [])

    def test_age_boundary_future_and_stale(self):
        self.assertEqual(self.compare(reference_block=drift.DEMO_REFERENCE + 10,
                                      max_age_blocks=10)['covered_count'], 1)
        for reference, max_age, reason in [
                (drift.DEMO_REFERENCE + 11, 10, 'later_snapshot_too_old'),
                (drift.DEMO_REFERENCE - 1, 10, 'later_snapshot_after_reference')]:
            result = self.compare(reference_block=reference, max_age_blocks=max_age)
            self.assertIn(reason, result['reasons'])
            self.assertEqual(result['candidates'], [])
            self.assertEqual(result['carried_bounds'], [])

    def test_reversed_and_same_height_refused(self):
        for before, after in [(self.after, self.before), (self.before, self.before)]:
            result = self.compare(before=before, after=after)
            self.assertIn('later_block_not_strictly_newer', result['reasons'])
            self.assertEqual(result['carried_bounds'], [])
        same_height_other_hash = deepcopy(self.after)
        same_height_other_hash['base']['block']['number'] = self.before['base']['block']['number']
        self.assertIn('later_block_not_strictly_newer',
                      self.compare(after=same_height_other_hash)['reasons'])

    def test_same_hash_or_timestamp_refused_at_newer_height(self):
        for key, reason in [('hash', 'same_block_hash'),
                            ('timestamp', 'later_timestamp_not_strictly_newer')]:
            after = deepcopy(self.after)
            after['base']['block'][key] = self.before['base']['block'][key]
            result = self.compare(after=after)
            self.assertIn(reason, result['reasons'])
            self.assertEqual(result['carried_bounds'], [])

    def test_corrupt_identity_decimals_and_header_are_errors(self):
        broken_pool = deepcopy(self.after)
        broken_pool['base']['initialize']['topics'][1] = '0x' + '1' * 64
        changed_decimals = deepcopy(self.after)
        changed_decimals['base']['raw']['zto_decimals'] = '0x' + drift.review.sizes.path.z.word(17).hex()
        broken_header = deepcopy(self.after)
        broken_header['base']['block']['number'] = ' 0x18f927d '
        for snapshot in (broken_pool, changed_decimals, broken_header):
            with self.assertRaises(ValueError):
                self.compare(after=snapshot)

    def test_bool_and_out_of_range_controls_are_errors(self):
        for key in ('slippage_bps', 'max_deterioration_bps', 'reference_block', 'max_age_blocks'):
            for value in (True, False, -1, 1.5, '100'):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.compare(**{key: value})
        for key in ('slippage_bps', 'max_deterioration_bps'):
            with self.assertRaises(ValueError):
                self.compare(**{key: 10000})

    def test_duplicate_amounts_stay_ordered_and_independent(self):
        result = self.compare(amounts=['1', '1.0', '100000000', '1'])
        self.assertEqual([r['candidate_index'] for r in result['carried_bounds']], [0, 1, 2, 3])
        rows = result['candidates']
        for index in (1, 3):
            self.assertEqual(rows[index]['before_output_raw'], rows[0]['before_output_raw'])
            self.assertEqual(rows[index]['after_output_raw'], rows[0]['after_output_raw'])
        self.assertEqual(result['after']['snapshot_sha256'], drift.review.digest(self.after))

    def test_bad_amounts_reject_whole_comparison_even_if_stale(self):
        for amounts in ([], ['0'], ['1e3'], ['1', 'nonsense'], [True], ['1'] * 21):
            with self.subTest(amounts=amounts), self.assertRaises(ValueError):
                self.compare(amounts=amounts, reference_block=drift.DEMO_REFERENCE + 1)

    def test_strict_json_reader_rejects_ambiguity_and_large_inputs(self):
        with tempfile.TemporaryDirectory(dir=drift.HERE) as temp:
            filename = Path(temp) / 'input.json'
            for data in ('{"a":1,"a":2}', '{"a":1.0}', '{"a":NaN}', ' ' * 100001):
                filename.write_text(data)
                with self.assertRaises(ValueError):
                    drift.review.read_json(filename)

    def test_cli_demo_is_offline_and_has_partial_refusal(self):
        out = io.StringIO()
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            with redirect_stdout(out):
                code = drift.main(['--demo'])
        result = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result['covered_count'], 2)
        self.assertEqual(result['candidates'][2]['reasons'], ['before_incomplete', 'after_incomplete'])
        self.assertEqual(result['mode'], 'historical_demo')

    def test_cli_custom_refusal_and_usage_error(self):
        command = ['--before', str(drift.BEFORE), '--after', str(drift.AFTER), '--amount', '1',
                   '--input', 'IMD', '--slippage-bps', '100', '--max-deterioration-bps', '100',
                   '--reference-block', str(drift.DEMO_REFERENCE), '--max-age-blocks', '0']
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(drift.main(command), 2)
            self.assertEqual(drift.main(['--demo', '--input', 'IMD']), 1)
        self.assertEqual(json.loads(out.getvalue())['carried_bounds'], [])
        self.assertIn('--demo cannot', json.loads(err.getvalue())['error'])


if __name__ == '__main__':
    unittest.main()
