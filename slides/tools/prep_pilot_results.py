"""Export the frozen 20-case Astra review. No inference calls.
Run: python -m slides.tools.prep_pilot_results --source-root <benchmark/20-cases checkout>
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMES = {'kimi-k3.1-pro': 'Kimi K3.1 Pro', 'deepseek-v4.1-flash-1017': 'DeepSeek V4.1 Flash', 'glm-5.3': 'GLM 5.3', 'nemotron-3-super': 'Nemotron 3 Super', 'gpt-oss-120b': 'GPT-OSS-120B'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, default=ROOT)
    source = parser.parse_args().source_root
    result = json.loads((source/'benchmark/judge/results.json').read_text())
    usage = json.loads((source/'benchmark/runs/twenty-case-pilot/manifest.json').read_text())
    assert len(result['grades']) == 100
    models = []
    for row in result['summary']:
        assert row['n'] == 20
        models.append({'id': row['model'], 'name': NAMES[row['model']], 'axes': {'suitability': row['axis_means']['suitability'], 'steps': row['axis_means']['procedural_soundness'], 'numerical_soundness': row['axis_means']['numerical_soundness']}, 'total': row['mean_total_out_of_6'], 'maximum': 6, 'critical_failures': row['cases_with_critical_failure']})
    payload = {'models': models, 'cases_per_model': 20, 'responses_per_case': 1, 'grader': 'Blinded Astra medium; provisional, not expert-validated', 'prompt_sha256': result['prompt_sha256'], 'new_generation_tokens': usage['new_prompt_tokens'] + usage['new_completion_tokens'], 'new_generation_estimate_usd': usage['estimated_new_cost_usd'], 'unconfirmed_allowance_usd': usage['unconfirmed_cost_reservation_usd'], 'judge_usage': 'Token counts and billing unavailable; no additional Nebius calls', 'source_commit': 'c1a0e32', 'source_report': 'https://github.com/sanjyotshenoy/what_we_test_next/blob/c1a0e32/benchmark/judge/RESULTS.md'}
    out = ROOT/'slides/talks/biohack/data'
    text = json.dumps(payload, indent=2) + '\n'
    (out/'pilot_results.json').write_text(text)
    (out/'pilot_results.js').write_text('window.DATA=window.DATA||{};window.DATA.pilotResults='+text.strip()+';\n')
    print('Exported 100 Astra reviews; means out of 6 and axis means out of 2.')

if __name__ == '__main__':
    main()
