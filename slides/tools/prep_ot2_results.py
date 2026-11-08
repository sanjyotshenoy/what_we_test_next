"""Prepare slide data from Jimmy's supplied MIC leaderboard (2026-11-08).

Run from repo root: python3 -m slides.tools.prep_ot2_results
Source: benchmark/step3_MIC_benchmark/candidates_step3/leaderboard.csv.
Scores are supplied simulator benchmark results, not independently reproduced.
"""
import csv
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[2]
    source = root / 'benchmark/step3_MIC_benchmark/candidates_step3/leaderboard.csv'
    with source.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    data = {'source': str(source.relative_to(root)), 'models': [
        {'name': r['Model'], 'before': float(r['Before: score /100']),
         'after': float(r['After: score /100']), 'repairs': int(r['Repair rounds']),
         'before_gate': r['Before: gate'], 'after_gate': r['After: gate']}
        for r in rows
    ]}
    out = root / 'slides/talks/biohack/data/ot2_results'
    encoded = json.dumps(data, indent=2) + '\n'
    out.with_suffix('.json').write_text(encoded)
    out.with_suffix('.js').write_text('window.DATA = window.DATA || {};\nwindow.DATA.ot2Results = ' + encoded.rstrip() + ';\n')


if __name__ == '__main__':
    main()
