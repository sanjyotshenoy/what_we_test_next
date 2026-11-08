# MIC benchmark on Nebius models: before and after the repair rule

Task: the step-3 prompt, word for word, one sample per model, reasoning effort high. Scored with `rubrics/step3_rubric.csv` (16 weighted rows, total weight 20.5, shown here out of 100).

| | Before | After |
|---|---|---|
| Simulator error | Whole protocol scores 0 | Error message goes back to the model, which returns a fix (up to 3 rounds). Each round used: -5 points. Still failing after 3 rounds: 0 |
| Cost | First answer only | First answer + every repair round |

## Results

| Model | Before | Repair rounds | After: rubric | Penalty | **After: score** | First answer | Repairs | **Total cost** |
|---|---|---|---|---|---|---|---|---|
| Kimi K3.1 Pro | 68.3 (pass) | 0 | 68.3 | 0 | **68.3** (pass) | $0.1098 | $0.0000 | **$0.1098** |
| DeepSeek V4.1 Flash 1017 | 0.0 (fail) | 1 | 69.5 | -5 | **64.5** (pass) | $0.0307 | $0.0136 | **$0.0442** |
| GLM 5.3 | 0.0 (fail) | 2 | 61.0 | -10 | **51.0** (pass) | $0.0861 | $0.1507 | **$0.2368** |
| GPT-OSS-120B | 0.0 (fail) | 3 | 25.6 | -15 | **10.6** (pass) | $0.0183 | $0.0156 | **$0.0339** |
| Nemotron 3 Super | 0.0 (fail) | 3 | 0.0 | 0 | **0.0** (fail) | $0.0046 | $0.0168 | **$0.0214** |
| Standard answer (reference) | 100.0 (pass) | 0 | 100.0 | 0 | **100.0** | | | |

Total spent on Nebius: **$0.4461**. Costs = Nebius list price x tokens the API reported. Each repair call resends the whole conversation, so input tokens grow every round. Cached input tokens are counted at full price, so repair costs are an upper bound.

## Repair rounds

**DeepSeek V4.1 Flash 1017**

- Round 1 ($0.0136): fed back `LocationTypeError [line 37]: location should be a Well, Location, TrashBin or WasteChute, but it is [A2 of Corning 96 Well Plate 360 µL Flat on slot 2, B2 of Co` -> passes

**GLM 5.3**

- Round 1 ($0.0451): fed back `UnexpectedTipAttachError [line 38]: Error 3012 UNEXPECTED_TIP_ATTACH (UnexpectedTipAttachError): Cannot perform pick up tip with a tip already attached.` -> still fails: `The robot run cannot start: the protocol requires a p300_single_gen2 on the right mount, but that pipette is not attache`
- Round 2 ($0.1056): fed back `The robot run cannot start: the protocol requires a p300_single_gen2 on the right mount, but that pipette is not attached. Only the 8-channel pipette from the l` -> passes

**GPT-OSS-120B**

- Round 1 ($0.0056): fed back `AttributeError [line 128]: 'ProtocolContext' object has no attribute 'trash_container'` -> still fails: `ProtocolCommandFailedError [line 87]: Error 4000 GENERAL_ERROR (ProtocolCommandFailedError): TipNotAttachedError: Pipett`
- Round 2 ($0.0048): fed back `ProtocolCommandFailedError [line 87]: Error 4000 GENERAL_ERROR (ProtocolCommandFailedError): TipNotAttachedError: Pipette should have a tip attached, but does n` -> still fails: `OutOfTipsError [line 174]:`
- Round 3 ($0.0053): fed back `OutOfTipsError [line 174]:` -> passes

**Nemotron 3 Super**

- Round 1 ($0.0043): fed back `RuntimeError [line 83]: Invalid target for multichannel transfer: [B1 of Corning 96 Well Plate 360 µL Flat on 3]` -> still fails: `The robot run cannot start: the protocol requires a p300_single_gen2 on the left mount, but that pipette is not attached`
- Round 2 ($0.0061): fed back `The robot run cannot start: the protocol requires a p300_single_gen2 on the left mount, but that pipette is not attached. Only the 8-channel pipette from the la` -> still fails: `OutOfTipsError [line 103]:`
- Round 3 ($0.0064): fed back `OutOfTipsError [line 103]:` -> still fails: `OutOfTipsError [line 102]:`

## Rubric rows after repair (0 / 0.5 / 1)

| Row | Weight | Kimi K3.1 Pro | DeepSeek V4.1 Flash 1017 | GLM 5.3 | GPT-OSS-120B | Standard answer |
|---|---|---|---|---|---|---|
| Plate layout | 2 | 1.0 | 1.0 | 1.0 | 0.0 | 1.0 |
| Two-fold dilution series | 2 | 1.0 | 1.0 | 0.5 | 0.0 | 1.0 |
| Growth / sterility controls | 2 | 1.0 | 1.0 | 0.5 | 0.0 | 1.0 |
| Final volume and inoculum ratio | 1 | 1.0 | 1.0 | 1.0 | 0.0 | 1.0 |
| 8-channel addressing | 2 | 1.0 | 1.0 | 1.0 | 0.0 | 1.0 |
| Cross-contamination | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 |
| Well volume <= 300 uL | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| MIC plate not in slots 1-3 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 |
| Tip box balanced | 0.5 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Labware close together | 0.5 | 0.5 | 1.0 | 1.0 | 1.0 | 1.0 |
| Mixing | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 |
| Reservoir volumes | 1.5 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Operator instructions | 0.5 | 0.5 | 0.5 | 1.0 | 0.5 | 1.0 |
| Tip choice for volumes | 0.5 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Estimated run time | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 |
| Tip count estimate | 1 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

## Notes per model

- **Kimi K3.1 Pro**: Ran cleanly first time (0 repairs). Antibiotics are hand-loaded into column 1 at a pause. Lost points: 8 bacteria tips reused across columns (64 contamination events into the bacteria trough), no mixing after bacteria, MIC plate in slot 1, tip rack in slot 3 not next to the plate, no load volumes in the file.
- **DeepSeek V4.1 Flash 1017**: 1 repair: dispense() was given a whole column list; the fix addresses each column by its row-A well. Then layout, 10-level series, controls and 1:1 inoculum are all correct. Lost points: one tip set reused for bacteria across 11 columns (80 contamination events into the bacteria trough), no mixing after bacteria, MIC plate in slot 2, no volumes in the file. Antibiotics come from a deep-well stock plate, not the reservoir.
- **GLM 5.3**: 2 repairs: (1) picked up a tip while still holding one; (2) the fix still loaded a p300_single_gen2, which the robot doesn't have. The final version is 8-channel only, with every load volume in comments. Lost points: an 11-level series across columns 1-11 with no sterility column, bacteria tips reused across columns (16 events into the trough), no mixing after bacteria, MIC plate in slot 2. Runs at apiLevel 2.13; scored at 2.14 so tip heights are known.
- **GPT-OSS-120B**: 3 repairs: trash_container doesn't exist, then a tip was missing, then it ran out of tips (added a 2nd rack). It passes the simulator but the liquid handling is wrong. An 8-channel transfer to single wells B1-H1 drives nozzles off the plate and carries antibiotics into other rows' wells (1,145 contamination events). The dilution loop also drains column 1 to 0 uL before the bacteria go in. No usable dilution series or controls: 25.6 on the rubric before the -15 repair penalty.
- **Nemotron 3 Super**: Still fails after 3 repairs. 8-channel transfer to well B1, then swapped in a single-channel p300 (not available), then ran out of tips with one rack. Scores 0.
