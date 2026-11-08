"""Build twenty reviewer cases and isolated input packets from committed graph CSVs.

Run: python3 -m slides.tools.prep_benchmark_cases
No model calls, no shared graph mutation, no live assay lookup.
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'slides/talks/biohack/graph/cases'
# TODO(final): human-review step abstractions and scoring rubric before treating these cases as validated.
CARDS = [
    {'id': 'kinase-prepare', 'template': 'proto:kinase_biochem_lum', 'action': 'Prepare a compound dilution series and vehicle/reference controls.', 'slots': ['top_concentration_uM', 'dilution_factor', 'n_points', 'replicates', 'vehicle_fraction']},
    {'id': 'kinase-react', 'template': 'proto:kinase_biochem_lum', 'action': 'Combine compound, kinase, substrate and ATP; run the reaction under justified conditions.', 'slots': ['enzyme_concentration', 'substrate_concentration', 'ATP_concentration', 'reaction_time', 'temperature'], 'requires': ['kinase-prepare']},
    {'id': 'kinase-detect', 'template': 'proto:kinase_biochem_lum', 'action': 'For ADP-Glo: stop the reaction and deplete residual ATP, then perform the ADP detection reaction and measure luminescence.', 'slots': ['reagent_volumes', 'depletion_time', 'detection_time'], 'requires': ['kinase-react']},
    {'id': 'cell-prepare', 'template': 'proto:cell_viability_atp', 'action': 'Prepare the specified cell system, dilution series, vehicle, reference and background controls.', 'slots': ['cell_density', 'medium', 'top_concentration_uM', 'dilution_factor', 'n_points', 'replicates', 'vehicle_fraction']},
    {'id': 'cell-expose', 'template': 'proto:cell_viability_atp', 'action': 'Expose cells to compound under justified culture conditions.', 'slots': ['exposure_time', 'temperature'], 'requires': ['cell-prepare']},
    {'id': 'cell-detect', 'template': 'proto:cell_viability_atp', 'action': 'For CellTiter-Glo: apply the ATP-based viability reagent, mix and stabilize according to a supported procedure, then measure luminescence.', 'slots': ['reagent_volume', 'mix_time', 'stabilization_time'], 'requires': ['cell-expose']},
    {'id': 'analyse', 'template': 'reviewer-authored', 'action': 'Normalize against appropriate controls, fit a concentration-response curve, and report uncertainty and assay limitations.', 'slots': ['fit_model', 'acceptance_criteria']},
]
SPECS = [
    ('case-1', 'Potent biochemical inhibition', 'CHEMBL4278808', 'Q8TF76', 'CHEMBL5357346',
     'Design a biochemical concentration-response experiment to measure inhibition of haspin by CHEMBL4278808. Propose an ordered procedure and justify its parameters; do not supply a remembered potency.',
     'Tests whether a proposed series resolves low-concentration activity rather than blindly copying a template default.', 'biochemical'),
    ('case-2', 'Different potency, same target', 'CHEMBL5426285', 'Q8TF76', 'CHEMBL5378515',
     'Design a biochemical concentration-response experiment to measure inhibition of human HASPIN by CHEMBL5426285. Propose an ordered procedure and justify its parameters; do not supply a remembered potency.',
     'Same target and reusable steps as case 1, but a different withheld potency. Tests whether numerical design uses available evidence and states uncertainty. A single well-designed series may legitimately cover both cases.', 'biochemical'),
    ('case-3', 'Cellular endpoint versus target inhibition', 'CHEMBL3936761', 'Q06187', 'CHEMBL5209939',
     'Design a concentration-response experiment to measure the effect of CHEMBL3936761 on growth/viability of Rec-1 cells. Explain what this experiment can and cannot establish about BTK inhibition.',
     'Tests assay suitability: a target-associated cellular measurement is not interchangeable with purified-enzyme inhibition or proof of a BTK-specific mechanism.', 'cellular'),
]


# Frozen additions; selection policy and limitations are documented in BENCHMARK.md.
EXTRA = json.loads(Path(__file__).with_name('benchmark_case_specs.json').read_text())
EXTRA_BY_ID = {x['id']: x for x in EXTRA}
for spec in EXTRA:
    cellular = spec['mode'] == 'cellular'
    question = (
        f"Design a concentration-response experiment to measure the effect of {spec['compound']} on growth/proliferation or viability of {spec['system']}. Explain the endpoint, justify the readout and any adaptations to the step cards, and state what this can and cannot establish about {spec['target_name']}."
        if cellular else
        f"Design a biochemical concentration-response experiment to measure inhibition of {spec['target_name']} ({spec['target']}) by {spec['compound']}. Propose an ordered procedure, justify the assay format and parameters, and explicitly identify unsupported conditions; do not supply a remembered potency."
    )
    rationale = (spec['focus'] + '. Tests suitability, supported step adaptation and numerical uncertainty; the hidden measurement is not a unique correct protocol.')
    SPECS.append((spec['id'], spec['focus'], spec['compound'], spec['target'], spec['assay'], question, rationale, spec['mode']))


def eligible_example(ap, mode, cid):
    if mode == 'biochemical':
        return ap.get('assay_type') == 'B' and ap.get('bao_format') == 'BAO_0000357'
    desc = ap.get('description', '').lower()
    if cid == 'case-3':
        return 'rec-1' in desc and 'viability' in desc
    # Require the explicit cell system and endpoint, not just a target association.
    terms = EXTRA_BY_ID[cid]['retrieval_terms']
    return (ap.get('bao_format') == 'BAO_0000219'
            and all(term in desc for term in terms)
            and any(term in desc for term in ('viability', 'proliferation', 'cell growth')))


def read_graph(part):
    folder = ROOT / 'kg' / part / 'graph'
    rows = []
    for kind in ('nodes', 'edges'):
        with (folder / f'{kind}.csv').open() as f:
            data = list(csv.DictReader(f))
        for r in data:
            r['props'] = json.loads(r['props'])
        rows.append(data)
    return rows


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def main():
    nodes, edges = read_graph('biology')
    by_id = {n['id']: n for n in nodes}
    OUT.mkdir(exist_ok=True)
    cases = []
    hashes = {}
    for part in ('biology', 'protocols'):
        for kind in ('nodes', 'edges'):
            p = ROOT / f'kg/{part}/graph/{kind}.csv'
            hashes[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    for cid, title, compound, target, assay, question, rationale, mode in SPECS:
        pair = [e for e in edges if e['rel'] == 'INHIBITS' and e['src'] == compound and e['dst'] == target]
        truth = next(e for e in pair if e['props']['assay'] == assay)
        documents = sorted({e['props']['document'] for e in pair})
        # Conservative document closure: remove every assay tied to any pair-supporting document.
        assays = {e['src'] for e in edges if e['rel'] == 'FROM_DOC' and e['dst'] in documents}
        assays.update(e['props']['assay'] for e in edges if e['props'].get('document') in documents and 'assay' in e['props'])
        excluded_nodes = set(documents) | assays
        def blocked(e):
            return (e['src'] in excluded_nodes or e['dst'] in excluded_nodes
                    or e['props'].get('document') in documents or e['props'].get('assay') in assays
                    or (e['rel'] == 'INHIBITS' and e['src'] == compound and e['dst'] == target))
        retained = [e for e in edges if not blocked(e)]
        # Explicitly a fixed retrieval baseline, not a claim of structural similarity.
        examples = []
        seen = set()
        for e in sorted(retained, key=lambda x: (x['src'], x['props'].get('assay', ''))):
            if e['rel'] != 'INHIBITS' or e['dst'] != target or e['src'] == compound or e['src'] in seen:
                continue
            a = by_id[e['props']['assay']]
            ap = a['props']
            eligible = eligible_example(ap, mode, cid)
            if cid in EXTRA_BY_ID and by_id[compound]['props'].get('smiles') and by_id[e['src']]['props'].get('smiles') == by_id[compound]['props']['smiles']:
                eligible = False
            if not eligible:
                continue
            examples.append({'compound': e['src'], 'ic50_nM': e['props']['ic50_nM'], 'assay': a['id'], 'description': ap.get('description'), 'document': e['props']['document'], 'source': e['source']})
            seen.add(e['src'])
            if len(examples) == 5:
                break
        inp = {'id': cid, 'question': question,
               'entities': [{'id': x, 'name': by_id[x]['name'], 'type': by_id[x]['type'], 'smiles': by_id[x]['props'].get('smiles')} for x in (compound, target)],
               'step_cards': CARDS,
               'retained_measurement_examples': examples,
               'retrieval_note': 'At most five other compounds on the same target, sorted by compound ID then assay ID. Not similarity-ranked. Assay descriptions are retained so compatibility can be assessed; their IC50s are contextual evidence, not direct estimates for the query. No eligible examples means insufficient retrieved evidence.',
               'guidelines': ['Match the biological system and readout to the question.', 'Use controls and justify the concentration series and replicates.', 'Respect prerequisites of chosen step cards; justify any adaptations.', 'State unsupported conditions as unresolved; do not invent source support.', 'Cell viability alone does not establish a target-specific mechanism.'],
               'output_contract': {'assay_type': 'string', 'system': 'string', 'readout': 'string', 'steps': [{'card_id': 'string or justified new step', 'instruction': 'string', 'parameters': 'value/unit/evidence or unresolved'}], 'top_concentration_uM': 'positive number', 'dilution_factor': 'number > 1', 'n_points': 'integer >= 2', 'replicates': 'positive integer', 'controls': ['string'], 'rationale': 'string', 'citations': ['provided evidence ID'], 'limitations': ['string']}}
        answer = {'reference_measurement': truth['props'], 'assay': by_id[assay],
                  'document': {'id': truth['props']['document'], 'title': by_id[truth['props']['document']]['name'], 'doi': (by_id[truth['props']['document']]['props'].get('doi') if isinstance(by_id[truth['props']['document']]['props'].get('doi'), str) else None)},
                  'expected_endpoint': 'Biochemical kinase inhibition; an independently justified compatible assay is acceptable.' if mode == 'biochemical' else 'Growth/viability in Rec-1 cells; purified-kinase inhibition alone does not answer this question. Do not claim BTK-specific causality from viability alone.',
                  'procedure_expectation': 'A coherent ordered procedure with relevant controls, parameter bindings and explicit unresolved conditions. Step cards are scaffolding, not a validated complete reference protocol.',
                  'numerical_reference': 'Held-out IC50 is a contextual target for coverage, not a required prediction or a complete parameter answer key. Full conditions and optimal ranges are not established by these CSV records.'}
        if cid in EXTRA_BY_ID and mode == 'cellular':
            answer['expected_endpoint'] = f"Growth/proliferation or viability in {EXTRA_BY_ID[cid]['system']}; purified-enzyme inhibition alone does not answer this question. A cellular response alone does not establish target-specific causality. Justify assay adaptation; do not equate all viability readouts."
        if cid in EXTRA_BY_ID:
            answer['review_limitations'] = [
                'Assay comparability is not established. Numerical coverage is descriptive, not a validated scientific score.',
                'Distinct document IDs and stored SMILES do not establish independent papers or chemical scaffolds.',
            ]
            if cid == 'case-5':
                answer['review_limitations'].append('The weak recorded activity does not justify an infeasible dose range; solubility, toxicity and assay limits remain unresolved.')
            if cid == 'case-9':
                answer['review_limitations'].append('The reference description mixes binding and enzyme inhibition. Numerical scientific comparison is not assessable until the endpoint is reviewed.')
            if cid in ('case-17', 'case-20'):
                answer['review_limitations'].append('Proliferation readout: do not silently substitute the ATP-luminescence detection card as the recorded method.')
            if cid == 'case-19':
                answer['review_limitations'].append('Sparse reference description does not establish a complete detection method or culture procedure.')
        audit = {'excluded_pair_measurements': len(pair), 'excluded_documents': documents, 'excluded_assays': sorted(assays), 'removed_edges': len(edges)-len(retained), 'remaining_edges': len(retained), 'remaining_nodes': len(nodes)-len(excluded_nodes & by_id.keys()), 'source_sha256': hashes,
                 'assertions': {'no_pair_edges': not any(e['rel']=='INHIBITS' and e['src']==compound and e['dst']==target for e in retained), 'no_excluded_sources_in_examples': all(e['document'] not in documents and e['assay'] not in assays for e in examples)}}
        assert all(audit['assertions'].values())
        item = {'id': cid, 'title': title, 'status': 'Draft / human review required', 'rationale': rationale, 'input': inp, 'answer': answer, 'audit': audit}
        dump(OUT / f'{cid}.input.json', inp)
        dump(OUT / f'{cid}.review.json', item)
        cases.append(item)
    manifest = {'version': 'v1-20-diagnostic', 'case_count': len(cases),
                'status': 'Draft / human domain review required; additions not model-evaluated',
                'counts_by_mode': {mode: sum(s[-1] == mode for s in SPECS) for mode in ('biochemical', 'cellular')},
                'source_sha256': hashes,
                'cases': [{'id': c['id'], 'mode': SPECS[i][-1],
                           'input_sha256': hashlib.sha256((OUT / (c['id'] + '.input.json')).read_bytes()).hexdigest(),
                           'reference_document': c['answer']['document']['id'],
                           'retained_examples': len(c['input']['retained_measurement_examples']),
                           'numerical_comparability': 'Not established; reviewer must assess assay/system compatibility'} for i, c in enumerate(cases)]}
    assert len(cases) == 20 and len({s[2] for s in SPECS}) == 20
    dump(OUT / 'manifest.json', manifest)
    (OUT / 'cases.js').write_text('window.BENCHMARK_CASES=' + json.dumps(cases, allow_nan=False) + ';\n')
    print('\n'.join(f"{c['id']}: {c['answer']['reference_measurement']['ic50_nM']} nM; {len(c['input']['retained_measurement_examples'])} input examples; {c['audit']['removed_edges']} edges removed" for c in cases))


if __name__ == '__main__':
    main()
