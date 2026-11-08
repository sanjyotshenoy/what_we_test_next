"""Transcribe Jimmy's chart supplied 2026-11-08 at 18:27 UTC into slide data.
Source image: slides/talks/pitch-preview/data/jimmy-plan-comparison.png.
Run from repo root: python3 -m slides.tools.prep_ot2_plan_results.
Preserve the supplied aggregate; it differs from the mean of displayed model values.
"""
import json
from pathlib import Path


def main():
    data = {
        'source': 'jimmy-plan-comparison.png',
        'samples_per_model_condition': 5,
        'aggregation': 'Drop the two lowest scores; average the remaining three.',
        'verification': 'Transcribed from supplied image; underlying runs not supplied.',
        # TODO(final): Reconcile supplied with-plan aggregate 46.7 with displayed model mean 46.06.
        'aggregate_note': 'All models is reported as supplied, not recalculated. The with-plan model scores average 46.06, not 46.7.',
        'models': [
            {'name': 'Kimi K3.1 Pro', 'label': ['Kimi', 'K3.1 Pro'], 'no_plan': 71.1, 'with_plan': 76.5},
            {'name': 'GLM 5.3', 'label': ['GLM 5.3'], 'no_plan': 55.3, 'with_plan': 73.0},
            {'name': 'DeepSeek V4.1', 'label': ['DeepSeek', 'V4.1'], 'no_plan': 74.1, 'with_plan': 76.1},
            {'name': 'GPT-OSS-120B', 'label': ['GPT-OSS', '120B'], 'no_plan': 0.0, 'with_plan': 8.0},
            {'name': 'Nemotron 3', 'label': ['Nemotron 3'], 'no_plan': 0.0, 'with_plan': 0.0},
            {'name': 'All models (reported)', 'label': ['All models*'], 'no_plan': 40.1, 'with_plan': 46.7},
        ],
    }
    out = Path(__file__).resolve().parents[1] / 'talks/pitch-preview/data/ot2_plan_results'
    encoded = json.dumps(data, indent=2) + '\n'
    out.with_suffix('.json').write_text(encoded)
    out.with_suffix('.js').write_text('window.DATA = window.DATA || {};\nwindow.DATA.ot2PlanResults = ' + encoded.rstrip() + ';\n')


if __name__ == '__main__':
    main()
