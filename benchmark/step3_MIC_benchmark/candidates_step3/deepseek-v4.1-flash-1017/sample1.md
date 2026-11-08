## MIC assay design for OT-2 with 8-channel pipette

### Critical labware note
With only **one 96-well plate + one 12-well reservoir + 8-channel pipette**, you **cannot automatically dispense different antibiotics into different rows**, because an 8-channel pipette always dispenses the same reagent to all 8 rows at once.

**Recommended solution:** Add an **additional 96-well deepwell source plate** (or an 8-well strip) to hold row-specific 2× antibiotic master mixes. The OT-2 can then aspirate all 8 different row-specific antibiotics simultaneously from one column of the source plate and dispense them into column 1 of the assay plate.

If you cannot add the source plate, you must manually prepare column 1 of the assay plate before running the OT-2.

---

## Plate layout

Rows A–H = 8 samples: 4 antibiotics × 2 replicates  
Columns 1–10 = 10 two-fold dilutions  
Column 11 = growth control (bacteria, no drug)  
Column 12 = sterility control (media only, no bacteria)

| Row | Sample |
|-----|--------|
| A | Antibiotic 1, replicate 1 |
| B | Antibiotic 1, replicate 2 |
| C | Antibiotic 2, replicate 1 |
| D | Antibiotic 2, replicate 2 |
| E | Antibiotic 3, replicate 1 |
| F | Antibiotic 3, replicate 2 |
| G | Antibiotic 4, replicate 1 |
| H | Antibiotic 4, replicate 2 |

Example final concentration range if the highest final concentration is **256 µg/mL**:

| Column | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|--------|---|---|---|---|---|---|---|---|---|----|----|----|
| Final drug conc. (µg/mL) | 256 | 128 | 64 | 32 | 16 | 8 | 4 | 2 | 1 | 0.5 | growth control | sterility control |

Prepare the source plate column 1 with **2× the highest final concentration** in medium. For the example above, add **512 µg/mL** antibiotic master mix to the appropriate source wells.

---

## Reagent preparation

### Source plate (96-well deepwell, column 1)
Add **≥250 µL per well** of the appropriate 2× antibiotic master mix in medium:

- A1, B1: Antibiotic 1, 2× highest concentration  
- C1, D1: Antibiotic 2, 2× highest concentration  
- E1, F1: Antibiotic 3, 2× highest concentration  
- G1, H1: Antibiotic 4, 2× highest concentration  

### 12-well reservoir
- Well A1: Media (≥15 mL)  
- Well A2: Bacterial inoculum at 2× final density (≥12 mL). For a final 5×10⁵ CFU/mL, prepare ~1×10⁶ CFU/mL. Mix well before run.  
- Well A12: Waste for discarded dilution volume  

### 96-well assay plate
Use a 360 µL flat-bottom or deepwell plate because final volume is 200 µL/well.

---

## OT-2 Python protocol

This protocol assumes:
- 8-channel P300 pipette (`p300_multi_gen2`) on the right mount
- 300 µL tip rack
- Assay plate in slot 2
- Source deepwell plate in slot 3
- 12-well reservoir in slot 4
- One 300 µL tip box is sufficient if tips are reused for media and serial dilution

```python
from opentrons import protocol_api

metadata = {
    'protocolName': 'MIC 2-fold dilution assay - 4 antibiotics x 2 replicates',
    'author': 'Opentrons prototype',
    'apiLevel': '2.14'
}

def run(protocol: protocol_api.ProtocolContext):
    # ------------------- Labware -------------------
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    assay_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2)
    source_plate = protocol.load_labware('nest_96_wellplate_2ml_deep', 3)  # row-specific 2x antibiotic master mixes
    reservoir = protocol.load_labware('usascientific_12_reservoir_22ml', 4)

    # ------------------- Pipette -------------------
    pipette = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=[tiprack])

    # ------------------- Reagents -------------------
    media = reservoir.wells()[0]      # A1
    bacteria = reservoir.wells()[1]   # A2
    waste = reservoir.wells()[11]     # A12

    # ------------------- Parameters -------------------
    media_vol = 100
    drug_vol = 200
    transfer_vol = 100
    inoculum_vol = 100
    mix_reps = 3
    mix_vol = 100
    num_concentrations = 10  # columns 1-10; columns 11-12 for controls

    # ------------------- 1. Fill media into columns 2-12 -------------------
    pipette.pick_up_tip()
    for col in range(1, 12):  # 0-indexed: columns 2 to 12
        pipette.aspirate(media_vol, media)
        pipette.dispense(media_vol, assay_plate.columns()[col])
        pipette.blow_out(media)
    pipette.drop_tip()

    # ------------------- 2. Add 2x antibiotic master mix to column 1 -------------------
    pipette.pick_up_tip()
    pipette.aspirate(drug_vol, source_plate.columns()[0])
    pipette.dispense(drug_vol, assay_plate.columns()[0])
    pipette.blow_out()
    pipette.drop_tip()

    # ------------------- 3. Serial dilution: col1 -> col2 ... -> col10 -------------------
    pipette.pick_up_tip()
    for i in range(num_concentrations - 1):
        source_col = assay_plate.columns()[i]
        dest_col = assay_plate.columns()[i + 1]
        pipette.aspirate(transfer_vol, source_col)
        pipette.dispense(transfer_vol, dest_col)
        pipette.mix(mix_reps, mix_vol, dest_col)
    # Discard 100 µL from the last concentration column to leave 100 µL
    last_col = assay_plate.columns()[num_concentrations - 1]
    pipette.aspirate(transfer_vol, last_col)
    pipette.dispense(transfer_vol, waste)
    pipette.blow_out(waste)
    pipette.drop_tip()

    # ------------------- 4. Add bacteria to columns 1-11 (growth control in col 11) -------------------
    pipette.pick_up_tip()
    pipette.mix(5, 200, bacteria)  # resuspend bacteria
    for col in range(11):  # 0-10: columns 1-11
        pipette.aspirate(inoculum_vol, bacteria)
        pipette.dispense(inoculum_vol, assay_plate.columns()[col])
        pipette.blow_out()
    pipette.drop_tip()

    # ------------------- 5. Add media to column 12 (sterility control) -------------------
    pipette.pick_up_tip()
    pipette.aspirate(media_vol, media)
    pipette.dispense(media_vol, assay_plate.columns()[11])
    pipette.blow_out(media)
    pipette.drop_tip()
```

---

## Notes and adjustments

- **Tip usage:** The script reuses one set of tips for media fill and one set for the entire serial dilution. This keeps the run within one 300 µL tip box. For higher dilution accuracy, use fresh tips between each serial transfer—this requires additional tip boxes.
- **If you need 12 concentrations and no controls:** Set `num_concentrations = 12`, change the serial dilution to go through column 12, and skip steps 4–5 control additions. Modify the bacteria addition to columns 1–12.
- **Concentration range:** Adjust the 2× antibiotic master mix concentration in the source plate to match your desired final MIC range. The highest final concentration is one-half of the source concentration after adding equal-volume inoculum.
- **Bacteria addition:** Ensure the bacterial suspension is well mixed before the run. The OT-2 performs a mix step, but manual resuspension immediately before starting is recommended.
- **Sterility and waste:** Use sterile media and reservoirs. Use a waste container or reservoir well for discarded dilution volume; ensure it has enough capacity (≥1 mL).