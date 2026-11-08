"""Unblind and aggregate only after every grade passes validation. No paid calls."""
import json,subprocess,sys
from collections import Counter,defaultdict
from pathlib import Path
from .validate import AXES,OUT,sha

def main():
    subprocess.run([sys.executable,'-m','benchmark.judge.validate','--complete'],check=True)
    mapping=json.loads((OUT/'private/mapping.json').read_text());manifest=json.loads((OUT/'manifest.json').read_text())
    rows=[]
    for job in manifest['jobs']:
        key=job['item_id'];grade=json.loads((OUT/'grades'/f'{key}.json').read_text());meta=mapping[key]
        rows.append({**meta,'item_id':key,'scores':{k:grade['axes'][k]['score'] for k in AXES},'total_out_of_6':sum(grade['axes'][k]['score'] for k in AXES),'critical_failure_count':len(grade['critical_failures']),'needs_human_review':grade['needs_human_review'],'low_confidence_axes':[k for k in AXES if grade['axes'][k]['confidence']=='low'],'grade_file':f'grades/{key}.json','grade_sha256':sha(OUT/'grades'/f'{key}.json')})
    groups=defaultdict(list)
    for r in rows:groups[r['model']].append(r)
    summary=[]
    for model,rs in groups.items():
        assert len(rs)==20
        modes={mode:[r for r in rs if (r['case_id'] in {'case-3','case-17','case-18','case-19','case-20'})==cell] for mode,cell in [('biochemical',False),('cellular',True)]}
        summary.append({'model':model,'n':len(rs),'axis_means':{k:sum(r['scores'][k] for r in rs)/len(rs) for k in AXES},'total_points_out_of_120':sum(r['total_out_of_6'] for r in rs),'mean_total_out_of_6':sum(r['total_out_of_6'] for r in rs)/len(rs),'cases_with_critical_failure':sum(r['critical_failure_count']>0 for r in rs),'cases_needing_human_review':sum(r['needs_human_review'] for r in rs),'cases_with_low_confidence_axis':sum(bool(r['low_confidence_axes']) for r in rs),'subgroups':{mode:{'n':len(ms),'axis_means':{k:sum(r['scores'][k] for r in ms)/len(ms) for k in AXES}} for mode,ms in modes.items()}})
    summary.sort(key=lambda r:(-r['mean_total_out_of_6'],r['model']))
    result={'judge':'gpt-6-astra','reasoning_effort':'medium','rubric_version':'v1','prompt_sha256':manifest['prompt_sha256'],'status':'Provisional AI judgments; not expert validated','summary':summary,'grades':sorted(rows,key=lambda r:(r['model'],int(r['case_id'].split('-')[1])))}
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    text=['# Astra-medium evaluation of the 20-case benchmark','','**Provisional AI-judge scores, not expert-validated performance or a deployment readiness claim.** All 100 saved responses were regraded under the same frozen rubric, including the original 15 pilot responses. The earlier Codex grades are retained unchanged in the historical run directories.','','## Scores','','Each axis is 0–2. The total is an illustrative equal-weight sum; critical failures are reported separately and must not be averaged into a passing result. No pass threshold or statistical superiority claim is defined.','','| Model | Suitability /2 | Procedure /2 | Numbers /2 | Mean total /6 | Points /120 | Cases with critical failure |','|---|---:|---:|---:|---:|---:|---:|']
    for r in summary:
        a=r['axis_means'];text.append(f"| {r['model']} | {a['suitability']:.2f} | {a['procedural_soundness']:.2f} | {a['numerical_soundness']:.2f} | {r['mean_total_out_of_6']:.2f} | {r['total_points_out_of_120']} | {r['cases_with_critical_failure']}/20 |")
    text+=['','## Assay subgroups','','| Model | Subgroup | Cases | Suitability /2 | Procedure /2 | Numbers /2 |','|---|---|---:|---:|---:|---:|']
    for r in summary:
        for mode,m in r['subgroups'].items():
            a=m['axis_means'];text.append(f"| {r['model']} | {mode} | {m['n']} | {a['suitability']:.2f} | {a['procedural_soundness']:.2f} | {a['numerical_soundness']:.2f} |")
    text+=['','## Method and limits','','- Frozen prompt: [PROMPT.md](PROMPT.md); hash and packet hashes in [manifest.json](manifest.json). Each response was scored by a fresh `gpt-6-astra` agent at medium reasoning, with no inherited conversation, model identity, prior grade or other response. The exposed model alias is recorded; an immutable provider snapshot is unavailable.','- Model mapping was withheld from judges. Blinding depends on tool-use restrictions and task isolation, not filesystem access controls. Judges may still infer model style; identity inference cannot be excluded.','- Generator input and final response were supplied alongside incomplete reviewer endpoint guidance. Hidden IC50 values and concentration-coverage diagnostics were deliberately excluded, so broad-range coverage does not directly improve the grade.','- Four synthetic fixtures checked predefined rubric anchors: wrong endpoint, invalid sequence, contradictory arithmetic, and honest incomplete design. This tests basic rubric comprehension, not expert agreement or comprehensive calibration. Only predefined anchor dimensions were checked; other scores on those fixtures are not claimed as validated.','- Every grade must contain literal response excerpts, a per-axis rationale, evidence paths, uncertainty and numerical checks. Automated validation verifies those structural properties and arithmetic; it does not certify scientific correctness.','- One judge sample per response. There is no inter-rater agreement estimate or repeated-judge variance measurement. The 20 purposively selected cases share assay families and are not an independent representative sample.','- Unresolved laboratory conditions and unknown assay compatibility remain not assessable. An honest partial design can score 1; grade 2 does not establish wet-lab efficacy or a ready-to-run protocol.','- Critical failures, low-confidence axes and human-review flags are recorded per response. Human domain review remains necessary before treating this ordering as a validated ranking.','','## Usage','','The judge used Codex collaboration agents, not Nebius. Requested model/effort and task provenance are in `execution.json`. This interface does not expose provider token counts or billing receipts for Astra; judge usage is **unavailable**, not zero-cost. No additional Nebius requests were made by the judge workflow. Generation receipts remain in `../runs/twenty-case-pilot/` (relative to the benchmark directory).','','## Per-case scores','','Links open the original judge JSON, including supporting quotes and rationales.','','| Model | Case | Suitability | Procedure | Numbers | Total /6 | Critical failures | Grade |','|---|---|---:|---:|---:|---:|---:|---|']
    for r in result['grades']:
        a=r['scores'];text.append(f"| {r['model']} | {r['case_id']} | {a['suitability']} | {a['procedural_soundness']} | {a['numerical_soundness']} | {r['total_out_of_6']} | {r['critical_failure_count']} | [evidence]({r['grade_file']}) |")
    (OUT/'RESULTS.md').write_text('\n'.join(text)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
