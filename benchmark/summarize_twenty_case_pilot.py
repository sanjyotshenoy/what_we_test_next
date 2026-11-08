"""Create the auditable report from completed receipts and offline diagnostics; no model calls."""
import json
from .check_twenty_case_pilot import RUN, check

def main():
    diagnostics = check()
    m = json.loads((RUN / 'manifest.json').read_text())
    report = ['# Twenty-case, five-model diagnostic benchmark', '',
              'Completed generation results for all 100 model/case combinations. Cases 1–3 reuse the original 15 outputs after checking byte-identical inputs, identical system prompt and settings. Cases 4–20 add 85 successful calls. Kimi cases 18 and 20 each had one timeout retry; case 19 had one retry after a local process interruption. All uncertain attempts are retained in the ledger. This is one completion per model/case, not repeated trials or a statistically validated leaderboard.', '',
              '<!-- TODO(final): domain reviewers must calibrate and apply the three-axis scientific rubric before reporting validated model quality scores. -->', '',
              '## Run conditions', '',
              'Same historical model IDs; temperature 0; reasoning_effort low; JSON-object mode; max_tokens 8192. Each request contains only its input packet and the fixed system instruction. No tools, web access, raw KB, reviewer answers or previous responses were supplied. All generation went through `wwtn.llm.chat`; no paid judge, SDK automatic retries or repair requests. Kimi case 18 had an explicit timeout retry (180 to 300 seconds), case 19 an interrupted-process recovery, and case 20 a timeout retry (300 to 600 seconds). Inference settings did not change; all uncertain attempts remain in the ledger. Model-returned IDs, timestamps, finish reasons and raw usage receipts are in `manifest.json`. Provider-reported completion tokens include reasoning; reasoning-token subsets must not be added again.', '',
              'Reused results were generated earlier and may differ from a fresh rerun even under the same nominal settings. Historical model names do not guarantee immutable provider weights. These are 15 biochemical and 5 cellular cases, not a validated MIC benchmark.', '',
              '## Automated diagnostics (not scientific rubric scores)', '',
              '| Model | JSON objects /20 | All contract fields /20 | Valid numeric series /20 | Numeric abstentions /20 | Descriptive IC50 coverage* | Step-prerequisite issue cases | Citation-format issue cases |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    summary = []
    for slug in m['model_mapping']:
        rs = [r for r in diagnostics if r['model'] == slug]
        valid = sum(r.get('valid_numeric_series', False) for r in rs)
        coverage = sum(r.get('brackets_reference') is True for r in rs)
        row = {'model': slug, 'valid_json': sum(r['valid_json'] for r in rs), 'complete_contract': sum(r.get('all_contract_fields_present', False) for r in rs), 'valid_numeric_series': valid, 'numeric_abstentions': sum(r.get('numeric_abstention_or_missing', False) for r in rs), 'descriptive_coverage': coverage, 'prerequisite_issue_cases': sum(bool(r.get('prerequisite_errors')) for r in rs), 'citation_format_issue_cases': sum(bool(r.get('non_exact_citations')) for r in rs)}
        summary.append(row)
        report.append(f"| {slug} | {row['valid_json']} | {row['complete_contract']} | {valid} | {row['numeric_abstentions']} | {coverage}/{valid} | {row['prerequisite_issue_cases']} | {row['citation_format_issue_cases']} |")
    report += ['', '*Coverage denominator is the number of valid numeric series, not all 20 cases. Coverage is merely the hidden IC50 lying between the smallest and largest proposed concentrations. Assay comparability is unestablished; case 9 explicitly mixes binding/inhibition source descriptions. Wider ranges can inflate coverage, and abstention may be appropriate. Do not interpret this as scientific accuracy or rank models by it.', '',
               'Abstentions include both null values and explicit “unresolved” strings. Nemotron has nine text-form abstentions in addition to three null-form abstentions; these are not silently counted as scientifically wrong. Its case 16 supplies numeric strings, which fail the strict numeric contract without implying bad arithmetic. Numeric validity checks positive finite concentration, dilution factor >1, integer point/replicate counts, and a computable positive series. It does not establish safe or appropriate laboratory settings. Citation-format issues mean a citation string is not exactly a provided ID; they are not automatically fabricated references. Alternative step cards may be legitimate adaptations. Contract presence does not establish type correctness or completeness of the protocol.', '',
               '## Three-axis rubric status and qualitative findings', '',
               'Subsequent evaluation: [Astra-medium scores for all 100 responses](../../judge/RESULTS.md), with a frozen rubric and per-case evidence. Those scores are provisional AI judgments, not expert validation. This generation report retains its original automated diagnostics.', '',
               'The agreed axes remain experiment suitability, procedural soundness and numerical soundness (0–2 each). No new scientific 0–2 grades or overall percentages are assigned by this automated report. The original three-case provisional grades remain historical and must not be presented as scores over 20 cases. Scientific grading needs review of evidence support, readout compatibility, units, controls and uncertainty, not just field presence or range coverage.', '',
               'The following are direct spot checks, not an exhaustive manual review:', '',
               '- GPT-OSS case 4 describes a 100 µM, three-fold, ten-point series as extending to approximately 0.02 µM and covering sub-nanomolar activity. The calculated minimum is 100/3^9 = 0.0050805 µM (5.08 nM), so those claims do not follow from its own parameters. Its readout also calls ADP production inversely related to kinase activity despite describing the opposite elsewhere.',
               '- GPT-OSS case 18 supplies specific cell density, medium and detection settings while citing a “standard BaF3 protocol” or manufacturer procedure. The input contains no retained measurement examples or manufacturer procedure; those settings are not supported by the packet.',
               '- Nemotron case 17 contains preparation, exposure and detection but omits the analysis step. It also supplies culture and detection settings that are absent from that zero-example packet.', '',
               '- Kimi case 17 labels its proposed numeric design as assumptions, leaves culture/detection settings unresolved, and explicitly distinguishes ATP response from direct Aurora A inhibition or target-specific causality. This is a useful handling of missing evidence, not proof that the proposed series is scientifically adequate.', '',
               'These examples show why syntactically complete, numerically computable proposals can still have substantive grounding problems. A definitive comparison requires applying the rubric consistently across every output.', '',
               '## Usage and cost', '',
               'Prices were checked against the live Nebius public catalog before generation. The conservative full-output reservation was $' + f"{m['estimated_conservative_reservation_usd']:.6f}" + ' against a $5 local cap. This gate bounds this batch at checked list prices; it does not read account balance or include teammates’ activity. Cached discounts are ignored; invoice totals may differ.', '',
               '| Model | New calls | New input tokens | New output tokens | New estimated USD | All-20 tokens (including reused) |', '|---|---:|---:|---:|---:|---:|']
    allcost = 0
    for slug in m['model_mapping']:
        allrows = [r for r in m['requests'] if r['slug'] == slug]
        fresh = [r for r in allrows if r['status'] == 'completed']
        p = sum(r['usage']['prompt_tokens'] for r in fresh);c = sum(r['usage']['completion_tokens'] for r in fresh)
        cost = sum(r['estimated_cost_usd'] for r in fresh)
        tokens = sum(r.get('usage', {}).get('prompt_tokens', 0) + r.get('usage', {}).get('completion_tokens', 0) for r in allrows)
        allcost += sum(r.get('estimated_cost_usd', 0) for r in allrows)
        report.append(f'| {slug} | {len(fresh)} | {p:,} | {c:,} | ${cost:.6f} | {tokens:,} |')
    report += ['', f"New batch: **{m['new_prompt_tokens'] + m['new_completion_tokens']:,} tokens; estimated ${m['estimated_new_cost_usd']:.6f}**. Including the original 15 calls, the aggregate generation estimate is ${allcost:.6f}. Reuse caused no additional billing. The $100 stated credit allocation is not a confirmed remaining balance.", '',
               f"Three prior attempts have unknown usage and billing. An additional ${m.get('unconfirmed_cost_reservation_usd', 0):.6f} is reserved for them; the receipt-based new cost plus this allowance is ${m['estimated_new_cost_usd'] + m.get('unconfirmed_cost_reservation_usd', 0):.6f}. Do not report the receipt-based total as a complete invoice.", '',
               '## Artifacts and reproduction', '',
               '- `manifest.json`: prompt, settings, current prices, response IDs, original reuse paths and per-request token/cost receipts.',
               '- `<model>/case-N.input.json`, `.output.txt`, `.output.json`: complete input snapshots and final outputs. Internal reasoning is not retained or used for review.',
               '- `diagnostics.json` and `summary.json`: per-case checks and aggregate counts.',
               '- `USAGE.md`: per-request usage ledger, distinguishing reused and new requests.',
               '- `python -m benchmark.summarize_twenty_case_pilot`: regenerate offline report and checks; no billing.',
               '- `python -m benchmark.run_twenty_case_pilot --execute`: paid runner, refuses an existing run unless explicitly resumed. Normal resume skips completed cases and refuses uncertain receipts; explicit recovery flags preserve failed attempts and enforce a revised cost reservation.', '']
    (RUN / 'RESULTS.md').write_text('\n'.join(report))
    (RUN / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    ledger = ['# Per-request usage ledger', '', 'Output counts include reasoning tokens where reported. Estimated costs use uncached list prices. Reused rows are historical charges, not new spend.', '', '| Model | Case | Origin | Input | Output | Historical/current estimate USD | New charge estimate USD |', '|---|---|---|---:|---:|---:|---:|']
    for r in sorted(m['requests'], key=lambda r: (r['slug'], int(r['case_id'].split('-')[1]))):
        if not r.get('usage'):
            ledger.append(f"| {r['slug']} | {r['case_id']} | {r['status']} | unknown | unknown | unknown | unknown |");continue
        u = r['usage'];cost = r['estimated_cost_usd'];new = 0 if r['status'] == 'reused' else cost
        ledger.append(f"| {r['slug']} | {r['case_id']} | {r['status']} | {u['prompt_tokens']} | {u['completion_tokens']} | ${cost:.7f} | ${new:.7f} |")
    for r in m.get('failed_attempts', []):
        ledger.append(f"| {r['slug']} | {r['case_id']} | {r['status']}; no receipt | unknown | unknown | unknown | reserved up to ${r['unconfirmed_cost_reservation_usd']:.7f} |")
    (RUN / 'USAGE.md').write_text('\n'.join(ledger) + '\n')

if __name__ == '__main__': main()
