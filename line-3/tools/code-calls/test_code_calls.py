"""Real proof replay and adversarial abstract-stack checks; fixtures are tests only."""
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
import code_calls as calls

FOLDER = Path(__file__).resolve().parent


def evidence(token='zto'):
    return calls.ancestry.read_json(FOLDER.parent / 'code-routes' / (token + '-proof.json'))


def push(value):
    width = max(1, (value.bit_length() + 7) // 8)
    return bytes([95 + width]) + value.to_bytes(width, 'big')


def target(expression, opcode=0xf1):
    result = calls.scan(expression + b'\x5a' + bytes([opcode]))['call_preview'][0]
    return int(result['target_word'], 16) if result['target_word'] is not None else None


class CallsTests(unittest.TestCase):
    def test_real_proofs(self):
        zto = calls.inspect(evidence())
        imd = calls.inspect(evidence('imd'))
        self.assertEqual(zto['runtimes'][0]['call_instruction_count'], 0)
        runtime = imd['runtimes'][0]
        self.assertEqual((runtime['call_instruction_count'], runtime['locally_constant_target_count'],
                          runtime['unresolved_target_count']), (12, 1, 11))
        constant = next(hit for hit in runtime['call_preview'] if hit['target_word'] is not None)
        self.assertEqual(constant['pc'], 12834)
        self.assertEqual(constant['target_address'], '0x1a44076050125825900e736c501f859c50fe728c')
        self.assertTrue(runtime['call_preview'][-1]['overlaps_recognized_metadata'])
        for result in (zto, imd):
            self.assertTrue(result['proof']['state_inclusion_verified'])
            self.assertFalse(result['external_target_code_verified'])
            self.assertFalse(result['reachability_verified'])
            self.assertFalse(result['semantic_safety_verified'])
            self.assertEqual(result['proof']['anchor'], 'unanchored-rpc-header')

    def test_all_four_call_variants_and_operand_order(self):
        for opcode in (0xf1, 0xf2, 0xf4, 0xfa):
            self.assertEqual(target(push(int(calls.lens.ZTO, 16)), opcode), int(calls.lens.ZTO, 16))
        # GAS is the top operand, the target is the next one.
        self.assertEqual(calls.scan(push(17) + push(99) + b'\xf1')['call_preview'][0]['target_word'],
                         '0x' + (17).to_bytes(32, 'big').hex())

    def test_address_uses_low_160_bits(self):
        word = (1 << 240) + int(calls.lens.ZTO, 16)
        hit = calls.scan(push(word) + b'\x5a\xf1')['call_preview'][0]
        self.assertEqual(hit['target_address'], calls.lens.ZTO)
        self.assertEqual(int(hit['target_word'], 16), word)

    def test_push_widths_and_push0(self):
        for width in range(1, 33):
            self.assertEqual(target(bytes([95 + width]) + (23).to_bytes(width, 'big')), 23)
        self.assertEqual(target(b'\x5f'), 0)  # Measured operand, never a recipient placeholder.

    def test_binary_operand_order_and_wrapping(self):
        cases = [(0x01, 3, 8, 11), (0x02, 3, 8, 24), (0x03, 3, 8, 5),
                 (0x04, 3, 8, 2), (0x06, 3, 8, 2), (0x10, 3, 8, 0),
                 (0x11, 3, 8, 1), (0x14, 3, 8, 0), (0x16, 3, 8, 0),
                 (0x17, 3, 8, 11), (0x18, 3, 8, 11), (0x1a, 0x1234, 30, 0x12),
                 (0x1b, 3, 8, 768), (0x1c, 768, 8, 3)]
        for opcode, lower, upper, expected in cases:
            self.assertEqual(target(push(lower) + push(upper) + bytes([opcode])), expected)
        self.assertEqual(target(push(calls.MASK) + push(1) + b'\x01'), 0)
        self.assertEqual(target(push(8) + push(3) + b'\x03'), calls.MASK - 4)
        for opcode in (0x04, 0x06):
            self.assertEqual(target(push(0) + push(8) + bytes([opcode])), 0)

    def test_shift_and_byte_bounds(self):
        for shift in (256, calls.MASK):
            for opcode in (0x1b, 0x1c):
                self.assertEqual(target(push(calls.MASK) + push(shift) + bytes([opcode])), 0)
        self.assertEqual(target(push(calls.MASK) + push(32) + b'\x1a'), 0)

    def test_modular_intermediate_is_not_wrapped(self):
        for opcode, expected in ((0x08, (2 * calls.MASK) % 17),
                                  (0x09, (calls.MASK * calls.MASK) % 17)):
            self.assertEqual(target(push(17) + push(calls.MASK) + push(calls.MASK)
                                    + bytes([opcode])), expected)
            self.assertEqual(target(push(0) + push(4) + push(5) + bytes([opcode])), 0)

    def test_unary_and_unknown_arithmetic(self):
        self.assertEqual(target(push(0) + b'\x15'), 1)
        self.assertEqual(target(push(7) + b'\x15'), 0)
        self.assertEqual(target(push(7) + b'\x19'), calls.MASK ^ 7)
        self.assertIsNone(target(push(7) + b'\x33\x01'))
        for opcode in (0x05, 0x07, 0x0a, 0x0b, 0x12, 0x13, 0x1d):
            self.assertIsNone(target(push(3) + push(4) + bytes([opcode])))

    def test_dup_and_swap_all_depths(self):
        for depth in range(1, 17):
            values = b''.join(push(value) for value in range(1, 18))
            self.assertEqual(target(values + bytes([0x7f + depth])), 18 - depth)
            self.assertEqual(target(values + bytes([0x8f + depth])), 17 - depth)

    def test_unknown_incoming_stack_and_repeated_pops(self):
        self.assertIsNone(target(b'\x80'))
        self.assertIsNone(target(push(7) + b'\x50\x50\x80'))
        self.assertIsNone(target(push(7) + b'\x81'))
        self.assertEqual(target(push(7) + b'\x91\x91'), 7)
        self.assertIsNone(target(push(7) + b'\x91'))

    def test_no_constant_crosses_control_boundaries(self):
        for opcode in (0x00, 0x56, 0x57, 0x5b, 0xf3, 0xfd, 0xfe, 0xff, 0x0c):
            self.assertIsNone(target(push(7) + bytes([opcode])))
            self.assertEqual(target(push(7) + bytes([opcode]) + push(13)), 13)

    def test_dynamic_sources_remain_unknown(self):
        for opcode in (0x30, 0x33, 0x35, 0x51, 0x54, 0x5c):
            self.assertIsNone(target(bytes([opcode])))
        self.assertEqual(target(push(42) + push(3) + b'\x54\x50'), 42)

    def test_memory_effect_does_not_invent_loaded_constant(self):
        self.assertIsNone(target(push(42) + push(0) + b'\x52' + push(0) + b'\x51'))

    def test_calls_leave_unknown_success_and_remove_arguments(self):
        hits = calls.scan(push(7) + b'\x5a\xf1\x5a\xf1')['call_preview']
        self.assertIsNone(hits[-1]['target_word'])
        code = push(42) + push(11) * 5 + push(7) + b'\x5a\xf1\x50\x5a\xf1'
        hits = calls.scan(code)['call_preview']
        self.assertEqual([int(hit['target_word'], 16) for hit in hits], [7, 42])

    def test_push_operands_are_not_calls_and_truncation_stops_decode(self):
        self.assertEqual(calls.scan(bytes.fromhex('63f1f2f4fa00'))['call_instruction_count'], 0)
        self.assertEqual(calls.scan(bytes.fromhex('7ff1f2f4fa'))['call_instruction_count'], 0)

    def test_pc_and_codesize(self):
        self.assertEqual(target(push(7) + b'\x50\x58'), 3)
        code = b'\x38\x5a\xf1'
        self.assertEqual(int(calls.scan(code)['call_preview'][0]['target_word'], 16), len(code))

    def test_analysis_and_preview_bounds(self):
        for code in (b'', '6001', b'\0' * 24577):
            with self.assertRaises(ValueError):
                calls.scan(code)
        for code in (b'\xef\x00', b'\xef\x01\x00', b'\xef'):
            with self.assertRaisesRegex(ValueError, 'different execution model'):
                calls.scan(code)
        result = calls.scan(b'\x5f\x5a\xf1' * 8192)
        self.assertEqual(result['call_instruction_count'], 8192)
        self.assertEqual(result['locally_constant_target_count'], 8192)
        self.assertEqual(len(result['call_preview']), 64)
        self.assertEqual(result['omitted_call_count'], 8128)
        self.assertLess(len(json.dumps(result)), 30000)
        self.assertIsNone(target(b'\x5f' * 1025))

    def test_proof_corruption_refused_before_output(self):
        for mutation in ('header', 'proof', 'runtime'):
            bundle = evidence()
            if mutation == 'header':
                bundle['header_rlp'] = bundle['header_rlp'][:-2] + 'ff'
            elif mutation == 'proof':
                bundle['proofs'][0]['accountProof'].pop()
            else:
                node = bundle['observation']['nodes'][0]
                code = b'\x5f\x5a\xf1'
                node.update(code='0x' + code.hex(), code_bytes=len(code), code_hash=calls.lens.digest(code))
                bundle['observation']['effective_code_hash'] = node['code_hash']
                bundle['proofs'][0]['codeHash'] = node['code_hash']
            with self.assertRaises(ValueError):
                calls.inspect(bundle)

    def test_anchor_matching_is_not_authenticity(self):
        bundle = evidence()
        result = calls.inspect(bundle, bundle['observation']['block']['hash'])
        self.assertEqual(result['proof']['anchor'], 'caller-supplied-block-hash')
        self.assertFalse(result['anchor_authenticity_verified'])
        other = calls.ancestry.read_json(FOLDER.parent / 'code-proof/zto-proof.json')
        with self.assertRaises(ValueError):
            calls.inspect(bundle, other['observation']['block']['hash'])

    def test_beacon_dedup_preserves_limits(self):
        spec = importlib.util.spec_from_file_location('proof_fixture',
                                                     FOLDER.parent / 'code-proof/test_code_proof.py')
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        result = calls.inspect(fixture.synthetic_beacon_bundle())
        self.assertEqual(len(result['runtimes']), 2)
        runtime = next(r for r in result['runtimes'] if r['address'] == calls.lens.IMD)
        self.assertEqual(set(runtime['roles']), {'beacon', 'candidate-path'})
        self.assertEqual(result['proof']['unproven_beacon_call_results'], [calls.lens.IMD])

    def test_workspace_and_duplicate_json_refusals(self):
        with self.assertRaises(ValueError):
            json.loads('{"x":1,"x":2}', object_pairs_hook=calls.ancestry.no_duplicates)
        with self.assertRaises(ValueError):
            calls.ancestry.read_json(Path.cwd().parent / 'outside.json')

    def test_cli_success_and_no_partial_failure(self):
        cmd = [sys.executable, '-B', str(FOLDER / 'code_calls.py'), '--bundle',
               str(FOLDER.parent / 'code-routes/imd-proof.json')]
        success = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertEqual(json.loads(success.stdout)['runtimes'][0]['call_instruction_count'], 12)
        failure = subprocess.run(cmd + ['--anchor-hash', 'bad'],
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(failure.returncode, 1)
        self.assertEqual(failure.stdout, '')

    def test_independent_concrete_stack_oracle(self):
        # Concrete top-first stacks, independently decoded, with different values
        # for the unknown incoming prefix and ADDRESS. A local constant must
        # agree with both executions, including DUP/SWAP and operand order.
        rng = random.Random(33)
        checked = 0
        for case in range(300):
            known = case % 2 == 0
            code = bytearray(b''.join(push(rng.randrange(2**32)) for _ in range(32))) if known else bytearray()
            depth = 32
            for _ in range(80):
                action = rng.randrange(7)
                if action <= 1 or depth < 4:
                    code.extend(push(rng.randrange(2**32)))
                    depth += 1
                elif action == 2:
                    code.append(rng.choice([0x01, 0x03, 0x16, 0x17, 0x18]))
                    depth -= 1
                elif action == 3:
                    code.append(0x80 + rng.randrange(min(depth, 16)))
                    depth += 1
                elif action == 4:
                    code.append(0x90 + rng.randrange(min(depth - 1, 16)))
                elif action == 5:
                    if known:
                        code.extend(push(rng.randrange(2**32)))
                    else:
                        code.append(0x33)
                    depth += 1
                else:
                    code.append(0x50)
                    depth -= 1
            code.extend(b'\x5a\xf1')
            abstract = calls.scan(bytes(code))['call_preview'][0]['target_word']
            for _ in range(2):
                stack = [rng.randrange(2**256) for _ in range(32)]
                caller, pc = rng.randrange(2**160), 0
                while pc < len(code):
                    opcode = code[pc]
                    pc += 1
                    if 96 <= opcode <= 127:
                        width = opcode - 95
                        stack.insert(0, int.from_bytes(code[pc:pc+width], 'big'))
                        pc += width
                    elif 128 <= opcode <= 143:
                        stack.insert(0, stack[opcode - 128])
                    elif 144 <= opcode <= 159:
                        i = opcode - 143
                        stack[0], stack[i] = stack[i], stack[0]
                    elif opcode in (0x01, 0x03, 0x16, 0x17, 0x18):
                        a, b = stack.pop(0), stack.pop(0)
                        if opcode == 1: value = a + b
                        elif opcode == 3: value = a - b
                        elif opcode == 0x16: value = a & b
                        elif opcode == 0x17: value = a | b
                        else: value = a ^ b
                        stack.insert(0, value % (2**256))
                    elif opcode == 0x33:
                        stack.insert(0, caller)
                    elif opcode == 0x50:
                        stack.pop(0)
                    elif opcode == 0x5a:
                        stack.insert(0, 123456)
                    elif opcode == 0xf1:
                        if abstract is not None:
                            self.assertEqual(int(abstract, 16), stack[1])
                            checked += 1
                    else:
                        self.fail('oracle received an unexpected opcode')
        self.assertGreaterEqual(checked, 300)

    def test_demo(self):
        import demo
        self.assertTrue(demo.main()['demonstration_passed'])


if __name__ == '__main__':
    unittest.main()
