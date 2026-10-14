"""Replay real saved ZTO-first, IMD-second state proofs without network access."""
import json
from pathlib import Path
import code_calls as calls


def main():
    results = []
    for token in ('zto', 'imd'):
        bundle = calls.ancestry.read_json(Path(__file__).resolve().parents[1]
                                          / 'code-routes' / (token + '-proof.json'))
        result = calls.inspect(bundle)
        runtime = result['runtimes'][0]
        results.append({'token': token.upper(), 'target': result['target'],
                        'code_block': result['code_block'],
                        'state_inclusion_verified': result['proof']['state_inclusion_verified'],
                        'anchor': result['proof']['anchor'],
                        'call_instruction_count': runtime['call_instruction_count'],
                        'locally_constant_target_count': runtime['locally_constant_target_count'],
                        'unresolved_target_count': runtime['unresolved_target_count'],
                        'calls': runtime['call_preview']})
    passed = (results[0]['call_instruction_count'] == 0
              and results[1]['call_instruction_count'] == 12
              and results[1]['locally_constant_target_count'] == 1
              and results[1]['calls'][9]['pc'] == 12834
              and results[1]['calls'][9]['target_address'] == '0x1a44076050125825900e736c501f859c50fe728c'
              and results[1]['calls'][-1]['overlaps_recognized_metadata']
              and all(r['state_inclusion_verified'] for r in results))
    return {'demonstration_passed': passed, 'results': results,
            'scope': 'Historical proof replay, not current code or verified external dependencies.'}


if __name__ == '__main__':
    result = main()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['demonstration_passed'] else 1)
