# Opentrons/: hand-written OT-2 protocols

**Owner:** Emmy Nguyen

Working OT-2 protocols written by hand, from the lab's existing protocol. They are the **reference** the generated
protocols are compared against (benchmark 2: "wells match the reference"), and the starting point for the robot
demo.

| File | What it is |
| --- | --- |
| `MIC_2Fold_Dilution_1Antibiotic_1Strain_200uL_modified.py` | OT-2 script (Python API, `apiLevel` 2.28): CLSI-style broth microdilution, 1 antibiotic × 1 strain, one 96-well plate, 2-fold series over columns 1–10, growth control in 11, sterility control in 12; P300 multi-channel, so rows A–H are 8 replicates; 200 µL final per well; pauses before the inoculum is added |
| `MIC_2Fold_Dilution_1Antibiotic_1Strain_Protocol.docx` | The written protocol for the script: deck layout (with a deck map), reagent preparation, pipette settings, each step, the final plate map, after-the-run reading, consumables |

Simplified from the Bridges lab (CMU) protocol `MIC_2Fold_Dilution_A4B4M4Am3Bm3_200uL.py`. The write-up refers to
the script as `MIC_2Fold_Dilution_1Antibiotic_1Strain_200uL.py`; the file here has `_modified` added. For the
demo, the inoculum can be swapped for food colouring.

Check it in the simulator (needs a recent `opentrons` package for API level 2.28):

```bash
pip install opentrons
opentrons_simulate Opentrons/MIC_2Fold_Dilution_1Antibiotic_1Strain_200uL_modified.py
```

The write-up says it was checked in the simulator (14 tip-column pickups, the pause, every transfer).

## Four-antibiotic reference package

Received from the team on 2026-11-08; the three supplied attachments are preserved unchanged.

| File | What it is |
| --- | --- |
| [MIC_4Abx_2Replicates_1Plate_200uL.py](MIC_4Abx_2Replicates_1Plate_200uL.py) | Hand-written OT-2 API 2.28 reference: four antibiotics, two replicate rows each (A+E, B+F, C+G, D+H), sparse antibiotic tips, 200 µL final volume, and fresh tips for each inoculum column. |
| [mic_4abx_ot2_full_layout_one_page.html](mic_4abx_ot2_full_layout_one_page.html) | Supplied browser-viewable layout and operator reference; open locally. External icon styling may require internet access. |
| [step3_rubric.csv](step3_rubric.csv) | Jimmy's supplied step-3 rubric, with a simulator gate, repair penalties, and weighted design, hardware, contamination, resource and efficiency criteria. |

This package adds a reference; it does not replace the original single-antibiotic protocol
or change the generated demo's separate-run compiler. The rubric is not yet wired into
an automated grader.

<!-- TODO(final): Validate this exact API 2.28 reference in a compatible simulator and
review the sparse-tip procedure on the intended hardware. This import checked Python
syntax and CSV structure only; the demo's pinned OT-2 environment targets API 2.27. -->
