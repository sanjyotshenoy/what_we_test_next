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
