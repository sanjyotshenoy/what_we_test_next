"""Offline receipt, provenance and output diagnostics; does not grade scientific correctness."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'benchmark/runs/twenty-case-pilot'

def check():
    manifest = json.loads((RUN / 'manifest.json').read_text());rows = []
    assert len(manifest['requests']) == 100
    assert len({(r['slug'], r['case_id']) for r in manifest['requests']}) == 100
    for rec in manifest['requests']:
        assert rec['status'] in ('completed', 'reused', 'failed_or_usage_unavailable'), (rec['slug'], rec['case_id'])
        folder = RUN / rec['slug'];cid = rec['case_id'];raw = (folder / f'{cid}.input.json').read_bytes()
        assert hashlib.sha256(raw).hexdigest() == rec['input_sha256']
        assert raw == (ROOT / f'slides/talks/biohack/graph/cases/{cid}.input.json').read_bytes()
        review = json.loads((ROOT / f'slides/talks/biohack/graph/cases/{cid}.review.json').read_text())
        assert not any(x in raw.decode() for x in review['audit']['excluded_documents'] + review['audit']['excluded_assays'])
        if rec['status'] == 'failed_or_usage_unavailable':
            rows.append({'model': rec['slug'], 'case_id': cid, 'origin': rec['status'], 'valid_json': False, 'generation_failure': rec['error_type'], 'source_exclusions_verified': True})
            continue
        assert rec['usage']['prompt_tokens'] > 0 and rec['usage']['completion_tokens'] >= 0
        inp = json.loads(raw);row = {'model': rec['slug'], 'case_id': cid, 'origin': rec['status'], 'finish_reason': rec['finish_reason'], 'source_exclusions_verified': True, 'withheld_source_ids_in_output': [x for x in review['audit']['excluded_documents'] + review['audit']['excluded_assays'] if x in (folder / f'{cid}.output.txt').read_text()]}
        try:
            out = json.loads((folder / f'{cid}.output.txt').read_text());assert isinstance(out, dict)
        except (ValueError, AssertionError):
            rows.append({**row, 'valid_json': False});continue
        cards = {c['id']: c for c in inp['step_cards']}
        steps = out.get('steps', []);steps = steps if isinstance(steps, list) else []
        used = [s.get('card_id') for s in steps if isinstance(s, dict)]
        errors = [f'{c} requires {req} earlier' for i, c in enumerate(used) if isinstance(c, str) for req in cards.get(c, {}).get('requires', []) if req not in used[:i]]
        t, f, n, r = [out.get(k) for k in ('top_concentration_uM', 'dilution_factor', 'n_points', 'replicates')]
        abstains = any(x is None or (isinstance(x, str) and x.strip().lower() in ('unresolved', 'unknown', 'not provided')) for x in (t, f, n, r))
        valid = type(t) in (int, float) and math.isfinite(t) and t > 0 and type(f) in (int, float) and math.isfinite(f) and f > 1 and type(n) is int and 2 <= n <= 10000 and type(r) is int and r > 0
        series = []
        if valid:
            try:
                series = [1000*t / f**i for i in range(n)]
                valid = all(math.isfinite(x) and x > 0 for x in series)
            except (OverflowError, ZeroDivisionError): valid = False
        truth = review['answer']['reference_measurement']['ic50_nM']
        citations = out.get('citations', [])
        # Exact provided identifier membership. Compound P/Q/O UniProt IDs all handled via entity list.
        allowed = set(cards) | {c['template'] for c in inp['step_cards']} | {e['id'] for e in inp['entities']}
        for e in inp['retained_measurement_examples']:
            allowed.update(e[k] for k in ('compound', 'assay', 'document'))
        citation_issues = [c for c in citations if not isinstance(c, str) or c not in allowed] if isinstance(citations, list) else ['citations is not a list']
        row.update({'valid_json': True, 'all_contract_fields_present': set(inp['output_contract']) <= out.keys(), 'steps_count': len(steps), 'has_analysis_card': 'analyse' in used, 'prerequisite_errors': errors, 'unknown_cards': [c for c in used if not isinstance(c, str) or c not in cards], 'non_exact_citations': citation_issues, 'numeric_abstention_or_missing': abstains, 'valid_numeric_series': bool(valid), 'reference_ic50_nM': truth, 'brackets_reference': min(series) <= truth <= max(series) if valid else None, 'two_each_side': sum(x < truth for x in series) >= 2 and sum(x > truth for x in series) >= 2 if valid else None, 'minimum_nM': min(series) if valid else None, 'maximum_nM': max(series) if valid else None, 'scientific_comparability': 'Not established; coverage is descriptive only, not an accuracy score.'})
        rows.append(row)
    fresh = [r for r in manifest['requests'] if r['status'] == 'completed']
    assert sum(r['status'] != 'reused' for r in manifest['requests']) == 85
    assert sum(r['usage']['prompt_tokens'] for r in fresh) == manifest['new_prompt_tokens']
    assert sum(r['usage']['completion_tokens'] for r in fresh) == manifest['new_completion_tokens']
    cost = 0
    for r in fresh:
        rate = manifest['rates'][r['model']]
        expected = (r['usage']['prompt_tokens'] * rate['input_price_per_million_tokens'] + r['usage']['completion_tokens'] * rate['output_price_per_million_tokens']) / 1e6
        assert math.isclose(expected, r['estimated_cost_usd'], abs_tol=1e-12)
        cost += expected
    assert math.isclose(cost, manifest['estimated_new_cost_usd'], abs_tol=1e-12)
    assert 85 + len(manifest.get('failed_attempts', [])) <= manifest['max_new_requests']
    assert cost + manifest.get('unconfirmed_cost_reservation_usd', 0) <= manifest['estimated_conservative_reservation_usd'] <= manifest['budget_ceiling_usd']
    (RUN / 'diagnostics.json').write_text(json.dumps(rows, indent=2, allow_nan=False) + '\n')
    for slug in manifest['model_mapping']:
        rs = [r for r in rows if r['model'] == slug]
        print(slug, json.dumps({'json': sum(r['valid_json'] for r in rs), 'complete_contract': sum(r.get('all_contract_fields_present', False) for r in rs), 'numeric_series': sum(r.get('valid_numeric_series', False) for r in rs), 'numeric_abstentions': sum(r.get('numeric_abstention_or_missing', False) for r in rs), 'brackets': sum(r.get('brackets_reference') is True for r in rs), 'prerequisite_error_cases': sum(bool(r.get('prerequisite_errors')) for r in rs), 'citation_format_issue_cases': sum(bool(r.get('non_exact_citations')) for r in rs)}))
    return rows

if __name__ == '__main__': check()
