# Ten-minute pitch: story draft

Main URL: https://zhang-etal-biohack.pages.dev/ — opens this combined deck. Original long URLs remain supported.

Preview branch: `slides-preview`. Entry: `index.html`. The original title slide opens the deck, followed by six pitch slides, a backup divider and the remaining nineteen original slides. Stop after the demo during the timed presentation; the standalone technical backup remains at `qa.html`. The existing main and question-prototype decks are unchanged.


## Running order

| Time | Slide | Job |
| --- | --- | --- |
| 0:00–0:50 | Relatable question + gap | Four beats: centered neutral plate; colors/labels and shift left; question with a hypothesized inhibitory connection and grey pathogen; “What experiment would answer this?” The grey state is hypothetical, not a measured outcome. |
| 0:50–2:00 | Missing link | Reuse the accepted five-state bipartite animation; compound and strains are supplied. |
| 2:00–3:00 | Evidence to proposal | Related compounds and measured activity; supporting papers; separate protocol templates; structured proposal. |
| 3:00–4:00 | Overall workflow | Existing answer vs missing measurement; proposed result-ingestion loop and upstream hypothesis refinement. |
| 4:00–5:15 | Hold-out pilot | Five models, three kinase/cell cases, provisional grades and one concrete inconsistency. |
| 5:15–8:15 | Evidence walkthrough | Inspect case input, retained evidence, withheld record and recorded output. Show the separate MIC execution artifact only with its provenance stated. |

Target 8:15 of rehearsed content, allow 45 seconds for transitions, retain one minute of recovery time. Speaker notes contain the three-minute demo sequence. No live API call is required.

## What is intentionally in Q/A

Graph construction and schema; protocol extraction and provenance; detailed three-axis rubric; per-model findings and costs; plate arithmetic; simulation assumptions and integration boundaries. CUDA timings are omitted because this draft has not verified a measured acceleration result relevant to the presented workflow.

## Claim boundaries

- The live premise is an unanswered question in an up-to-date KB. Hiding known evidence is a benchmark simulation.
- Reported pilot uses fixed isolated packets, not live retrieval or a measured KG ablation. Three correlated cases and uncalibrated Codex grades do not establish a statistical ranking.
- The tested GLM model is **GLM 5.3, not Flash**.
- The case walkthrough is kinase/cell evidence. The MIC run sheet is a separately generated hand-written-input example. Do not narrate them as a single agent-to-robot run.
- Compatibility blocking is the required workflow contract; the existing executor still needs hard gates. No hardware or clinical result is claimed.

## Review and editing

`hook.js`, `proposal.js` and `finish.js` hold pitch-specific content. The missing-link slide reuses `../question-prototype/story.js`; its original grounded-design slide is hidden in this pitch; the scores reuse `../biohack/data/pilot_results.js`. `qa.html` loads the current main deck's modules with an explicit base URL and hides the opening/closing narrative slides. Recheck the wrapper when the main deck's module list changes.

Run `python slides/tools/check_deck.py slides/talks/pitch-preview --back` from the repo root. Publish only on request; pushing this preview branch does not deploy the production deck.

The offline recorded output at `data/deepseek-case-2.output.json` is copied unchanged from `benchmark/runs/four-model-pilot/deepseek-v4.1-flash-1017/case-2.output.json` at main `8d59b20`. It is an actual pilot output, not a newly generated response.

## PowerPoint export

The animated PowerPoint export follows the current order, with the overall workflow before the benchmark. Present in Slide Show mode: click to reveal the captured HTML states. The images preserve the design; smooth HTML motion is represented by discrete reveals. Click the demo image to open the live explorer.

## Jimmy’s OT-2 results

`ot2-results.js` compares no plan (step 3 only) with an experiment plan (step 2 + 3).
The supplied screenshot is retained at `data/jimmy-plan-comparison.png`; regenerate
its transcribed JSON/JS using `python3 -m slides.tools.prep_ot2_plan_results`.
Five samples per model and condition; the two lowest are discarded and the other
three averaged. This replaces the earlier single-sample before/after repair chart.

<!-- TODO(final): Obtain underlying runs and reconcile the reported aggregate.
The supplied with-plan aggregate is 46.7, while displayed model scores average 46.06. -->
The chart preserves the supplied aggregate and flags it visibly. No wet-lab result
or statistical significance is established. The current editable animated PowerPoint includes this comparison. Older exports
still contain the earlier before/after repair chart.
